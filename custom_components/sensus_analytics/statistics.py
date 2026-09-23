"""Import Sensus hourly water usage into Home Assistant long-term statistics.

Sensus only publishes a day's hourly usage after that day has ended, so a sensor can never
report water at the hour it was used. Instead, each hour is written as an external statistic
(``sensus_analytics:<account>_<meter>_water_<unit>``) timestamped at the hour the water was
actually used, which lets the Energy dashboard match the Sensus portal day for day.

Every successful coordinator refresh schedules an import run in the background:

- Nothing is imported until the coordinator has the previous day's hourly data.
- A run is skipped when that data is unchanged since the last complete run, so morning
  corrections are picked up without rewriting the database on every poll.
- The first run backfills ``BACKFILL_DAYS`` days before the previous day; later runs fill any
  gap since the last imported hour (for example after Home Assistant was offline).
- The previous day is always rewritten, with the running sum rebuilt from the last statistic
  before the first rewritten hour, so corrections never double count.

The ``import_history`` action imports older history on demand (see ``async_import_history``):
it fetches every day from a chosen start date, writes nothing unless every day was fetched, and
rewrites every hour from the first day with data onwards so the running sum stays continuous.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, tzinfo
from typing import TYPE_CHECKING, Any

from homeassistant.components.recorder.models import StatisticData, StatisticMeanType, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
    statistics_during_period,
)
from homeassistant.core import callback
from homeassistant.helpers.recorder import get_instance
from homeassistant.util import dt as dt_util, slugify
from homeassistant.util.unit_conversion import VolumeConverter

from .api import SensusAnalyticsApiClientError
from .const import (
    CONF_ACCOUNT_NUMBER,
    CONF_METER_NUMBER,
    CONF_UNIT_TYPE,
    DEFAULT_UNIT_TYPE,
    DOMAIN,
    LOGGER,
    UNIT_CCF,
    UNIT_GALLONS,
)
from .data import get_config_value
from .utils.units import as_float, convert_volume, normalized_unit

if TYPE_CHECKING:
    from collections.abc import Coroutine

    from homeassistant.core import HomeAssistant

    from .data import SensusAnalyticsConfigEntry

BACKFILL_DAYS = 30
# History import: pause between day requests, retries per day, and base retry backoff (seconds)
HISTORY_REQUEST_DELAY = 0.5
HISTORY_RETRIES = 3
HISTORY_RETRY_DELAY = 2.0
# Hours written per recorder job: keeps each database transaction short on multi-year imports
IMPORT_CHUNK_SIZE = 31 * 24
STATISTIC_NAME = "Sensus Analytics water usage"
# Statistics keep more precision than the rounded sensor states (0.000001 CCF is about 0.0001 CF)
VALUE_PRECISION = 6

type HourlyUsage = dict[datetime, float]


def build_statistic_id(account_number: str, meter_number: str, unit: str) -> str:
    """Return the external statistic id for a meter and display unit.

    The unit is part of the id so switching display units starts a new series instead of
    mixing gallons and CCF in one.
    """
    account = slugify(str(account_number)) or "account"
    meter = slugify(str(meter_number)) or "meter"
    return f"{DOMAIN}:{account}_{meter}_water_{slugify(unit)}"


def build_metadata(statistic_id: str, unit: str, name: str = STATISTIC_NAME) -> StatisticMetaData:
    """Return the metadata for the water usage statistic."""
    return StatisticMetaData(
        mean_type=StatisticMeanType.NONE,
        has_sum=True,
        name=name,
        source=DOMAIN,
        statistic_id=statistic_id,
        unit_class=VolumeConverter.UNIT_CLASS,
        unit_of_measurement=unit,
    )


def display_unit(entry: SensusAnalyticsConfigEntry) -> str:
    """Return the configured display unit, matching the sensors."""
    if get_config_value(entry, CONF_UNIT_TYPE, DEFAULT_UNIT_TYPE) == UNIT_GALLONS:
        return UNIT_GALLONS
    return UNIT_CCF


def hourly_usage(
    entries: list[dict[str, Any]],
    target_unit: str,
    fallback_unit: Any = None,
) -> HourlyUsage | None:
    """Return usage per UTC hour start, converted to the target unit.

    Entries without a usage value or with a timestamp that isn't on the hour are skipped.
    Returns None when the Sensus unit can't be converted to the target unit.
    """
    usage_by_hour: HourlyUsage = {}
    for entry in entries:
        timestamp_ms = as_float(entry.get("timestamp"))
        usage = as_float(entry.get("usage"))
        if timestamp_ms is None or usage is None:
            continue
        start = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
        if start.minute or start.second or start.microsecond:
            continue
        source_unit = normalized_unit(entry.get("usage_unit")) or normalized_unit(fallback_unit)
        converted = convert_volume(usage, source_unit, target_unit)
        if converted is None:
            return None
        usage_by_hour[start] = round(converted, VALUE_PRECISION)
    return usage_by_hour


class SensusAnalyticsHistoryImportError(Exception):
    """A history import could not fetch every day, so nothing was written."""


@dataclass(frozen=True, slots=True)
class SensusAnalyticsHistoryImportResult:
    """The outcome of a history import."""

    # First local day with hourly data, or None when Sensus had none for the whole range
    first_day: date | None
    # Local days written, from the first day with data through the last day imported
    days: int


def _local_day_start(day: date, local_tz: tzinfo) -> datetime:
    """Return the start of a local day as an aware UTC datetime."""
    return dt_util.as_utc(datetime.combine(day, time.min, tzinfo=local_tz))


class SensusAnalyticsStatisticsImporter:
    """Import Sensus hourly water usage as an external long-term statistic."""

    def __init__(self, hass: HomeAssistant, entry: SensusAnalyticsConfigEntry) -> None:
        """Initialize the importer."""
        self._hass = hass
        self._entry = entry
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._history_task: asyncio.Task[None] | None = None
        # The previous day's data as of the last complete import
        self._fingerprint: tuple[Any, ...] | None = None
        self._unknown_unit_logged = False
        self.unit = display_unit(entry)
        self.statistic_id = build_statistic_id(
            entry.data[CONF_ACCOUNT_NUMBER],
            entry.data[CONF_METER_NUMBER],
            self.unit,
        )

    @property
    def _local_tz(self) -> tzinfo:
        """Return Home Assistant's configured time zone."""
        return dt_util.get_time_zone(self._hass.config.time_zone) or dt_util.DEFAULT_TIME_ZONE

    @property
    def statistic_name(self) -> str:
        """Return the statistic name shown in the Energy dashboard."""
        return self._name

    @property
    def history_import_running(self) -> bool:
        """Return whether a history import is in progress."""
        return self._history_task is not None and not self._history_task.done()

    @property
    def _name(self) -> str:
        """Return the statistic name, adding the meter number when there are several meters."""
        if len(self._hass.config_entries.async_entries(DOMAIN)) > 1:
            return f"{STATISTIC_NAME} {self._entry.data[CONF_METER_NUMBER]}"
        return STATISTIC_NAME

    @callback
    def async_handle_coordinator_update(self) -> None:
        """Schedule an import after a successful coordinator refresh without blocking it."""
        if not self._entry.runtime_data.coordinator.last_update_success:
            return
        if self._task is not None and not self._task.done():
            LOGGER.debug("Statistics import for %s is still running", self.statistic_id)
            return
        self._task = self._entry.async_create_background_task(
            self._hass,
            self.async_import(),
            f"{DOMAIN} statistics import {self._entry.entry_id}",
        )

    async def async_import(self) -> None:
        """Import any new or corrected hourly usage; runs never overlap."""
        async with self._lock:
            await self._async_import()

    @callback
    def async_start_history_import(self, target: Coroutine[Any, Any, None]) -> None:
        """Run a history import (wrapped by the caller for reporting) as a background task."""
        self._history_task = self._entry.async_create_background_task(
            self._hass,
            target,
            f"{DOMAIN} history import {self._entry.entry_id}",
        )

    async def async_import_history(self, start_date: date) -> SensusAnalyticsHistoryImportResult:
        """Import hourly usage from start_date through yesterday.

        Holds the import lock for the whole run, so a regular import triggered meanwhile waits
        for it and then only picks up anything newer. Raises SensusAnalyticsHistoryImportError,
        without writing anything, when any day can't be fetched.
        """
        async with self._lock:
            return await self._async_import_history(start_date)

    async def async_get_last_imported_hour(self) -> datetime | None:
        """Return the start of the last imported hour, if any."""
        last_start, _last_sum = await self._async_last_statistic()
        return last_start

    async def _async_last_statistic(self) -> tuple[datetime | None, float]:
        """Return the start and running sum of the newest imported hour."""
        last_stats = await get_instance(self._hass).async_add_executor_job(
            get_last_statistics,
            self._hass,
            1,
            self.statistic_id,
            True,
            {"sum"},
        )
        rows = last_stats.get(self.statistic_id)
        if not rows or (start := rows[0].get("start")) is None:
            return None, 0.0
        return dt_util.utc_from_timestamp(start), float(rows[0].get("sum") or 0)

    async def _async_import(self) -> None:
        """Import the hourly usage (called with the lock held)."""
        coordinator_data = self._entry.runtime_data.coordinator.data or {}
        fallback_unit = coordinator_data.get("usageUnit")
        yesterday = hourly_usage(coordinator_data.get("hourly_usage_data") or [], self.unit, fallback_unit)
        if yesterday is None:
            self._warn_unknown_unit()
            return
        if not yesterday:
            # The hourly fetch is best effort, and Sensus has nothing until the day is released
            LOGGER.debug("No hourly usage to import for %s", self.statistic_id)
            return

        fingerprint = (self.statistic_id, tuple(sorted(yesterday.items())))
        if fingerprint == self._fingerprint:
            LOGGER.debug("Hourly usage for %s is unchanged, skipping import", self.statistic_id)
            return

        local_tz = self._local_tz
        data_day = min(yesterday).astimezone(local_tz).date()
        last_start, last_sum = await self._async_last_statistic()
        first_day = self._first_day_to_fetch(data_day, last_start)
        if first_day is None:
            LOGGER.debug("Statistics for %s are newer than the hourly data, skipping import", self.statistic_id)
            return

        days = [first_day + timedelta(days=offset) for offset in range((data_day - first_day).days)]
        usage, complete = await self._async_fetch_days(days, fallback_unit)
        if complete:
            usage.update(yesterday)
        if not usage:
            return

        write_start = _local_day_start(first_day, local_tz)
        running_sum = await self._async_sum_before(write_start, last_start, last_sum)
        statistics: list[StatisticData] = []
        for start in sorted(usage):
            if start < write_start:
                continue
            running_sum += usage[start]
            statistics.append(StatisticData(start=start, state=usage[start], sum=round(running_sum, VALUE_PRECISION)))

        LOGGER.debug("Adding %s hourly statistics for %s from %s", len(statistics), self.statistic_id, write_start)
        async_add_external_statistics(self._hass, build_metadata(self.statistic_id, self.unit, self._name), statistics)
        if complete:
            self._fingerprint = fingerprint

    def _first_day_to_fetch(self, data_day: date, last_start: datetime | None) -> date | None:
        """Return the first local day to write, or None when the statistics are already ahead."""
        local_tz = self._local_tz
        oldest_day = data_day - timedelta(days=BACKFILL_DAYS)
        if last_start is None:
            return oldest_day
        if last_start >= _local_day_start(data_day + timedelta(days=1), local_tz):
            return None

        last_day = last_start.astimezone(local_tz).date()
        next_day = last_day + timedelta(days=1)
        # Fetch the last imported day again when it stopped short of midnight
        first_day = last_day if last_start + timedelta(hours=1) < _local_day_start(next_day, local_tz) else next_day
        return min(max(first_day, oldest_day), data_day)

    async def _async_fetch_days(self, days: list[date], fallback_unit: Any) -> tuple[HourlyUsage, bool]:
        """Fetch hourly usage for past local days, one request at a time.

        Stops at the first failure so the running sum only ever covers contiguous days; the
        remaining days are retried on the next run. Returns the usage and whether every day
        was fetched.
        """
        client = self._entry.runtime_data.client
        usage: HourlyUsage = {}
        for index, day in enumerate(days):
            try:
                entries = await client.async_get_hourly_data(
                    account_number=self._entry.data[CONF_ACCOUNT_NUMBER],
                    meter_number=self._entry.data[CONF_METER_NUMBER],
                    target_date=datetime.combine(day, time(12), tzinfo=self._local_tz),
                    authenticate=index == 0,
                )
            except SensusAnalyticsApiClientError as exception:
                LOGGER.warning(
                    "Failed to fetch Sensus hourly data for %s, will retry on the next update: %s",
                    day.isoformat(),
                    exception,
                )
                return usage, False
            day_usage = hourly_usage(entries, self.unit, fallback_unit)
            if day_usage is None:
                self._warn_unknown_unit()
                return usage, False
            usage.update(day_usage)
        return usage, True

    async def _async_import_history(self, start_date: date) -> SensusAnalyticsHistoryImportResult:
        """Import history (called with the lock held)."""
        local_tz = self._local_tz
        coordinator_data = self._entry.runtime_data.coordinator.data or {}
        fallback_unit = coordinator_data.get("usageUnit")
        yesterday = hourly_usage(coordinator_data.get("hourly_usage_data") or [], self.unit, fallback_unit)
        if yesterday is None:
            self._warn_unknown_unit()
            raise SensusAnalyticsHistoryImportError("the Sensus usage unit is not supported")

        # The newest day comes from the coordinator, like the regular import. Without it, the
        # previous day may not be published yet (or only partly), so stop the day before and
        # leave it to the regular import once the coordinator has it.
        if yesterday:
            data_day: date | None = min(yesterday).astimezone(local_tz).date()
            last_day = data_day
            last_fetch_day = data_day - timedelta(days=1)
        else:
            data_day = None
            last_day = last_fetch_day = dt_util.now(local_tz).date() - timedelta(days=2)

        days = [start_date + timedelta(days=offset) for offset in range((last_fetch_day - start_date).days + 1)]
        usage_by_day = await self._async_fetch_history(days, fallback_unit)
        use_coordinator_day = data_day is not None and data_day >= start_date
        if use_coordinator_day:
            usage_by_day.append((last_day, yesterday))

        # Skip leading days without data, so nothing is written before the first real hour
        first_day = next((day for day, day_usage in usage_by_day if day_usage), None)
        if first_day is None:
            LOGGER.debug("Sensus had no hourly usage for %s since %s", self.statistic_id, start_date)
            return SensusAnalyticsHistoryImportResult(first_day=None, days=0)
        usage: HourlyUsage = {}
        for day, day_usage in usage_by_day:
            if day >= first_day:
                usage.update(day_usage)

        await self._async_write_history(usage)
        if use_coordinator_day:
            # The next regular run skips this data but still imports later corrections
            self._fingerprint = (self.statistic_id, tuple(sorted(yesterday.items())))
        return SensusAnalyticsHistoryImportResult(first_day=first_day, days=(last_day - first_day).days + 1)

    async def _async_fetch_history(self, days: list[date], fallback_unit: Any) -> list[tuple[date, HourlyUsage]]:
        """Fetch every day, one request at a time, retrying each day before giving up."""
        usage_by_day: list[tuple[date, HourlyUsage]] = []
        for index, day in enumerate(days):
            if index:
                await asyncio.sleep(HISTORY_REQUEST_DELAY)
            # Log in once at the start; retries log in again in case the session expired
            entries = await self._async_fetch_history_day(day, authenticate=index == 0)
            day_usage = hourly_usage(entries, self.unit, fallback_unit)
            if day_usage is None:
                self._warn_unknown_unit()
                raise SensusAnalyticsHistoryImportError("the Sensus usage unit is not supported")
            usage_by_day.append((day, day_usage))
        return usage_by_day

    async def _async_fetch_history_day(self, day: date, *, authenticate: bool) -> list[dict[str, Any]]:
        """Fetch one day, retrying with a growing delay and a fresh login."""
        client = self._entry.runtime_data.client
        attempt = 0
        while True:
            try:
                return await client.async_get_hourly_data(
                    account_number=self._entry.data[CONF_ACCOUNT_NUMBER],
                    meter_number=self._entry.data[CONF_METER_NUMBER],
                    target_date=datetime.combine(day, time(12), tzinfo=self._local_tz),
                    authenticate=authenticate or attempt > 0,
                )
            except SensusAnalyticsApiClientError as exception:
                if attempt >= HISTORY_RETRIES:
                    raise SensusAnalyticsHistoryImportError(
                        f"failed to fetch hourly data for {day.isoformat()}: {exception}",
                    ) from exception
                LOGGER.debug("Retrying Sensus hourly data for %s: %s", day.isoformat(), exception)
                await asyncio.sleep(HISTORY_RETRY_DELAY * 2**attempt)
                attempt += 1

    async def _async_write_history(self, usage: HourlyUsage) -> None:
        """Rewrite every hour from the first imported hour onwards with a continuous running sum.

        Hours already in the statistic after that point (for example from the regular import)
        keep their values but get their sums rebuilt, so the sum never jumps.
        """
        recorder = get_instance(self._hass)
        # Let any queued import finish so the sums read below are current
        await recorder.async_block_till_done()
        first_hour = min(usage)
        last_start, last_sum = await self._async_last_statistic()
        running_sum = await self._async_sum_before(first_hour, last_start, last_sum)

        stats = await recorder.async_add_executor_job(
            statistics_during_period,
            self._hass,
            first_hour,
            None,
            {self.statistic_id},
            "hour",
            None,
            {"state"},
        )
        merged: HourlyUsage = {
            dt_util.utc_from_timestamp(start): float(row.get("state") or 0)
            for row in stats.get(self.statistic_id, [])
            if (start := row.get("start")) is not None
        }
        merged.update(usage)

        statistics: list[StatisticData] = []
        for start in sorted(merged):
            running_sum += merged[start]
            statistics.append(StatisticData(start=start, state=merged[start], sum=round(running_sum, VALUE_PRECISION)))

        LOGGER.debug("Adding %s hourly statistics for %s from %s", len(statistics), self.statistic_id, first_hour)
        # The recorder runs its jobs in order, and every sum is already final, so chunks stay consistent
        for index in range(0, len(statistics), IMPORT_CHUNK_SIZE):
            async_add_external_statistics(
                self._hass,
                build_metadata(self.statistic_id, self.unit, self._name),
                statistics[index : index + IMPORT_CHUNK_SIZE],
            )
        await recorder.async_block_till_done()

    def _warn_unknown_unit(self) -> None:
        """Log once that the Sensus usage unit can't be converted to the display unit."""
        if not self._unknown_unit_logged:
            self._unknown_unit_logged = True
            LOGGER.warning("Can't import Sensus hourly usage into statistics: the usage unit is not supported")

    async def _async_sum_before(self, start: datetime, last_start: datetime | None, last_sum: float) -> float:
        """Return the running sum of the last statistic before start."""
        if last_start is None:
            return 0.0
        if last_start < start:
            return last_sum

        # Rewriting hours that were already imported: continue from the statistic before them,
        # looking at the previous day first and then at the whole history
        for period_start in (start - timedelta(days=1), dt_util.utc_from_timestamp(0)):
            stats = await get_instance(self._hass).async_add_executor_job(
                statistics_during_period,
                self._hass,
                period_start,
                start,
                {self.statistic_id},
                "hour",
                None,
                {"sum"},
            )
            if rows := stats.get(self.statistic_id):
                return float(rows[-1].get("sum") or 0)
        return 0.0
