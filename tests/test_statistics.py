"""Tests for importing Sensus hourly usage into long-term statistics, including the import_history action."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Generator
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import async_wait_recording_done

from custom_components.sensus_analytics import statistics as sensus_statistics
from custom_components.sensus_analytics.api import SensusAnalyticsApiClient, SensusAnalyticsApiClientCommunicationError
from custom_components.sensus_analytics.const import (
    CONF_ACCOUNT_NUMBER,
    CONF_BASE_URL,
    CONF_METER_NUMBER,
    CONF_UNIT_TYPE,
    DOMAIN,
    SERVICE_IMPORT_HISTORY,
    UNIT_CCF,
    UNIT_GALLONS,
)
from custom_components.sensus_analytics.diagnostics import async_get_config_entry_diagnostics
from custom_components.sensus_analytics.statistics import (
    BACKFILL_DAYS,
    HISTORY_RETRIES,
    IMPORT_CHUNK_SIZE,
    STATISTIC_NAME,
    build_metadata,
    build_statistic_id,
    hourly_usage,
)
from homeassistant.components import persistent_notification
from homeassistant.components.recorder import Recorder
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import statistics_during_period, valid_statistic_id
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.recorder import get_instance
from homeassistant.util import dt as dt_util

TIME_ZONE = "America/Los_Angeles"
ENTRY_DATA = {
    CONF_BASE_URL: "https://city.sensus-analytics.com/",
    CONF_USERNAME: "user",
    CONF_PASSWORD: "pass",
    CONF_ACCOUNT_NUMBER: "123",
    CONF_METER_NUMBER: "456",
    CONF_UNIT_TYPE: UNIT_CCF,
}
CCF_STATISTIC_ID = "sensus_analytics:123_456_water_ccf"

UsageFn = Callable[[date, int], float]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock: Recorder, enable_custom_integrations: None) -> None:
    """Load the integration under test with a real (in-memory) recorder."""


def _local_tz() -> Any:
    """Return the test time zone."""
    return dt_util.get_time_zone(TIME_ZONE)


def _day_start(day: date) -> datetime:
    """Return the start of a local day in UTC."""
    return dt_util.as_utc(datetime.combine(day, time.min, tzinfo=_local_tz()))


def _default_usage(day: date, hour_index: int) -> float:
    """Return deterministic cubic feet per hour for a day."""
    return day.day + hour_index / 10


def _day_entries(day: date, usage_fn: UsageFn = _default_usage, unit: str = "CF") -> list[dict[str, Any]]:
    """Return normalized Sensus hourly entries for every hour of a local day (23-25 hours)."""
    entries: list[dict[str, Any]] = []
    hour = _day_start(day)
    end = _day_start(day + timedelta(days=1))
    while hour < end:
        entries.append(
            {
                "timestamp": int(hour.timestamp() * 1000),
                "usage": usage_fn(day, len(entries)),
                "rain": 0.0,
                "temp": 60.0,
                "usage_unit": unit,
                "rain_unit": "in",
                "temp_unit": "F",
            },
        )
        hour += timedelta(hours=1)
    return entries


class FakeSensus:
    """Deterministic stand-in for the Sensus endpoints."""

    def __init__(self, yesterday: date) -> None:
        """Serve yesterday's data through the coordinator and past days through the hourly fetch."""
        self.yesterday = yesterday
        self.usage_fn: UsageFn = _default_usage
        self.hourly: list[dict[str, Any]] | None = _day_entries(yesterday)
        self.fetched: list[date] = []
        self.authenticated: list[bool] = []
        self.fail_on: set[date] = set()

    def set_yesterday(self, yesterday: date) -> None:
        """Move to a new day."""
        self.yesterday = yesterday
        self.hourly = _day_entries(yesterday, self.usage_fn)

    async def get_data(self, **_: Any) -> dict[str, Any]:
        """Return what async_get_data returns."""
        data: dict[str, Any] = {"dailyUsage": 100, "billingUsage": 500, "usageUnit": "CF"}
        if self.hourly is not None:
            data["hourly_usage_data"] = self.hourly
        return data

    async def get_hourly_data(self, *, target_date: datetime, authenticate: bool = True, **_: Any) -> list[dict]:
        """Return one past day's entries."""
        day = target_date.date()
        self.fetched.append(day)
        self.authenticated.append(authenticate)
        if day in self.fail_on:
            raise SensusAnalyticsApiClientCommunicationError("boom")
        return _day_entries(day, self.usage_fn)


@pytest.fixture
async def fake_sensus(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> Generator[FakeSensus]:
    """Patch the Sensus client with deterministic data for 2026-09-21 as "yesterday"."""
    await hass.config.async_set_time_zone(TIME_ZONE)
    freezer.move_to(datetime(2026, 9, 22, 10, 30, tzinfo=_local_tz()))
    fake = FakeSensus(date(2026, 9, 21))
    with (
        patch.object(SensusAnalyticsApiClient, "async_get_data", AsyncMock(side_effect=fake.get_data)),
        patch.object(SensusAnalyticsApiClient, "async_get_hourly_data", AsyncMock(side_effect=fake.get_hourly_data)),
    ):
        yield fake


async def _setup(hass: HomeAssistant, data: dict[str, Any] | None = None) -> MockConfigEntry:
    """Set up a config entry and wait for the first statistics import."""
    entry = MockConfigEntry(domain=DOMAIN, data=data or ENTRY_DATA, unique_id="123_456")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await _wait(hass)
    assert entry.state is ConfigEntryState.LOADED
    return entry


async def _wait(hass: HomeAssistant) -> None:
    """Wait for the background import and the recorder."""
    await hass.async_block_till_done(wait_background_tasks=True)
    await async_wait_recording_done(hass)


async def _refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Poll Sensus again and wait for the import it schedules."""
    await entry.runtime_data.coordinator.async_refresh()
    await _wait(hass)


async def _rows(hass: HomeAssistant, statistic_id: str = CCF_STATISTIC_ID) -> list[dict[str, Any]]:
    """Return all hourly rows of a statistic."""
    stats = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        dt_util.utc_from_timestamp(0),
        None,
        {statistic_id},
        "hour",
        None,
        {"state", "sum"},
    )
    return stats.get(statistic_id, [])


def _assert_chained(rows: list[dict[str, Any]]) -> None:
    """Every row's sum is the previous sum plus its own state."""
    previous_sum = 0.0
    for row in rows:
        assert row["sum"] == pytest.approx(previous_sum + row["state"])
        previous_sum = row["sum"]


def _expected_ccf(day: date, usage_fn: UsageFn = _default_usage) -> list[float]:
    """Return a day's expected hourly values in CCF."""
    return [entry["usage"] / 100 for entry in _day_entries(day, usage_fn)]


@pytest.mark.parametrize(
    ("unit", "statistic_id"),
    [
        (UNIT_CCF, "sensus_analytics:123_456_water_ccf"),
        (UNIT_GALLONS, "sensus_analytics:123_456_water_gal"),
    ],
)
def test_statistic_id_and_metadata(unit: str, statistic_id: str) -> None:
    """The display unit is part of the id and the metadata describes a volume sum."""
    assert build_statistic_id("123", "456", unit) == statistic_id
    assert valid_statistic_id(statistic_id)

    metadata = build_metadata(statistic_id, unit)
    assert metadata["statistic_id"] == statistic_id
    assert metadata["source"] == DOMAIN
    assert metadata["name"] == STATISTIC_NAME
    assert metadata["unit_of_measurement"] == unit
    assert metadata["unit_class"] == "volume"
    assert metadata["has_sum"] is True
    assert metadata["mean_type"] is StatisticMeanType.NONE


def test_statistic_id_is_a_valid_slug() -> None:
    """Account and meter numbers with dashes, spaces, or capitals still give a valid id."""
    statistic_id = build_statistic_id("AB-12 34", "M-9", UNIT_GALLONS)
    assert statistic_id == "sensus_analytics:ab_12_34_m_9_water_gal"
    assert valid_statistic_id(statistic_id)


@pytest.mark.parametrize(
    ("usage_unit", "target", "expected"),
    [
        ("CF", UNIT_GALLONS, 9.230962),
        ("CF", UNIT_CCF, 0.01234),
        ("GAL", UNIT_CCF, 0.00165),
        ("CCF", UNIT_GALLONS, 923.096168),
    ],
)
def test_hourly_usage_keeps_precision(usage_unit: str, target: str, expected: float) -> None:
    """Hourly values are converted without the sensors' integer/2-decimal rounding."""
    timestamp = datetime(2026, 9, 21, 7, tzinfo=UTC)
    entries = [{"timestamp": int(timestamp.timestamp() * 1000), "usage": 1.234, "usage_unit": usage_unit}]

    result = hourly_usage(entries, target)

    assert result is not None
    assert result[timestamp] == pytest.approx(expected, abs=1e-6)


def test_hourly_usage_skips_unusable_entries_and_rejects_unknown_units() -> None:
    """Missing usage and off-the-hour timestamps are skipped; an unknown unit aborts."""
    on_hour = int(datetime(2026, 9, 21, 7, tzinfo=UTC).timestamp() * 1000)
    entries = [
        {"timestamp": on_hour, "usage": None, "usage_unit": "CF"},
        {"timestamp": on_hour + 60_000, "usage": 1, "usage_unit": "CF"},
    ]
    assert hourly_usage(entries, UNIT_CCF) == {}
    # The daily "usageUnit" is the fallback when an entry has no unit
    assert hourly_usage([{"timestamp": on_hour, "usage": 100}], UNIT_CCF, "CF") == {
        datetime(2026, 9, 21, 7, tzinfo=UTC): 1.0,
    }
    assert hourly_usage([{"timestamp": on_hour, "usage": 1, "usage_unit": "M3"}], UNIT_CCF) is None


async def test_first_run_backfills_with_chained_sum(hass: HomeAssistant, fake_sensus: FakeSensus) -> None:
    """The first import backfills the previous days plus yesterday at the hour the water was used."""
    await _setup(hass)

    first_day = date(2026, 9, 21) - timedelta(days=BACKFILL_DAYS)
    assert fake_sensus.fetched == [first_day + timedelta(days=offset) for offset in range(BACKFILL_DAYS)]
    # One login for the whole backfill, then plain requests
    assert fake_sensus.authenticated == [True] + [False] * (BACKFILL_DAYS - 1)

    rows = await _rows(hass)
    days = [first_day + timedelta(days=offset) for offset in range(BACKFILL_DAYS + 1)]
    expected = [value for day in days for value in _expected_ccf(day)]
    assert [row["state"] for row in rows] == pytest.approx(expected)
    assert rows[0]["start"] == _day_start(first_day).timestamp()
    # Midnight-to-1 AM on the 21st (Pacific) is 07:00 UTC, matching the Sensus portal's bar
    assert rows[-24]["start"] == datetime(2026, 9, 21, 7, tzinfo=UTC).timestamp()
    assert rows[-1]["start"] == datetime(2026, 9, 22, 6, tzinfo=UTC).timestamp()
    _assert_chained(rows)
    assert rows[-1]["sum"] == pytest.approx(sum(expected))


async def test_gallons_statistic_uses_gallons(hass: HomeAssistant, fake_sensus: FakeSensus) -> None:
    """A gallons display unit gets its own series in gallons."""
    await _setup(hass, {**ENTRY_DATA, CONF_UNIT_TYPE: UNIT_GALLONS})

    rows = await _rows(hass, "sensus_analytics:123_456_water_gal")
    assert rows[-24]["state"] == pytest.approx(round(21 * 7.48052, 6))
    assert await _rows(hass) == []


async def test_correction_rewrites_yesterday_without_double_counting(
    hass: HomeAssistant,
    fake_sensus: FakeSensus,
) -> None:
    """A morning correction to yesterday replaces its hours and the running sum stays consistent."""
    entry = await _setup(hass)
    before = await _rows(hass)
    fetched = len(fake_sensus.fetched)

    corrected = [dict(item) for item in fake_sensus.hourly or []]
    corrected[5]["usage"] += 50  # +0.5 CCF
    corrected[23]["usage"] += 100  # +1 CCF
    fake_sensus.hourly = corrected
    await _refresh(hass, entry)

    after = await _rows(hass)
    assert len(after) == len(before)
    # Earlier days are untouched
    assert after[:-24] == before[:-24]
    assert after[-24 + 5]["state"] == pytest.approx(before[-24 + 5]["state"] + 0.5)
    assert after[-1]["sum"] == pytest.approx(before[-1]["sum"] + 1.5)
    _assert_chained(after)
    # Rewriting yesterday doesn't need any other day
    assert len(fake_sensus.fetched) == fetched


async def test_unchanged_data_is_not_imported_again(hass: HomeAssistant, fake_sensus: FakeSensus) -> None:
    """Polls that bring the same hourly data don't touch the database."""
    entry = await _setup(hass)

    with patch.object(
        sensus_statistics,
        "async_add_external_statistics",
        wraps=sensus_statistics.async_add_external_statistics,
    ) as add_statistics:
        await _refresh(hass, entry)
        await _refresh(hass, entry)
        assert add_statistics.call_count == 0

        # New data for the same day is imported
        fake_sensus.hourly = [{**item, "usage": item["usage"] + 1} for item in fake_sensus.hourly or []]
        await _refresh(hass, entry)
        assert add_statistics.call_count == 1


async def test_gap_is_filled_after_days_offline(
    hass: HomeAssistant,
    fake_sensus: FakeSensus,
    freezer: FrozenDateTimeFactory,
) -> None:
    """When the last statistic is several days old, only the missing days are fetched."""
    entry = await _setup(hass)
    fake_sensus.fetched.clear()
    fake_sensus.authenticated.clear()

    freezer.move_to(datetime(2026, 9, 26, 10, 30, tzinfo=_local_tz()))
    fake_sensus.set_yesterday(date(2026, 9, 25))
    await _refresh(hass, entry)

    assert fake_sensus.fetched == [date(2026, 9, 22), date(2026, 9, 23), date(2026, 9, 24)]
    assert fake_sensus.authenticated == [True, False, False]
    rows = await _rows(hass)
    assert len(rows) == (BACKFILL_DAYS + 5) * 24
    assert rows[-1]["start"] == datetime(2026, 9, 26, 6, tzinfo=UTC).timestamp()
    assert [row["state"] for row in rows[-4 * 24 :]] == pytest.approx(
        [value for day in range(22, 26) for value in _expected_ccf(date(2026, 9, day))],
    )
    _assert_chained(rows)


async def test_partial_last_day_is_fetched_again(
    hass: HomeAssistant,
    fake_sensus: FakeSensus,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A day that was only partly published when imported is completed on the next day."""
    fake_sensus.hourly = _day_entries(date(2026, 9, 21))[:20]
    entry = await _setup(hass)
    fake_sensus.fetched.clear()

    freezer.move_to(datetime(2026, 9, 23, 10, 30, tzinfo=_local_tz()))
    fake_sensus.set_yesterday(date(2026, 9, 22))
    await _refresh(hass, entry)

    assert fake_sensus.fetched == [date(2026, 9, 21)]
    rows = await _rows(hass)
    assert len(rows) == (BACKFILL_DAYS + 2) * 24
    _assert_chained(rows)


@pytest.mark.parametrize(
    ("today", "hours"),
    [
        # Clocks fall back on 2025-11-02 (25 hours) and spring forward on 2026-03-08 (23 hours)
        (date(2025, 11, 3), 25),
        (date(2026, 3, 9), 23),
    ],
)
async def test_dst_days_import_every_hour(
    hass: HomeAssistant,
    fake_sensus: FakeSensus,
    freezer: FrozenDateTimeFactory,
    today: date,
    hours: int,
) -> None:
    """Days with a DST change import all of their 23 or 25 hours."""
    yesterday = today - timedelta(days=1)
    freezer.move_to(datetime.combine(today, time(10, 30), tzinfo=_local_tz()))
    fake_sensus.set_yesterday(yesterday)
    assert len(fake_sensus.hourly or []) == hours

    await _setup(hass)

    rows = await _rows(hass)
    yesterday_rows = [row for row in rows if row["start"] >= _day_start(yesterday).timestamp()]
    assert len(yesterday_rows) == hours
    assert [row["state"] for row in yesterday_rows] == pytest.approx(_expected_ccf(yesterday))
    _assert_chained(rows)


async def test_nothing_imported_without_hourly_data(hass: HomeAssistant, fake_sensus: FakeSensus) -> None:
    """If the hourly fetch failed or Sensus hasn't published the day, nothing is imported yet."""
    fake_sensus.hourly = None
    entry = await _setup(hass)
    fake_sensus.hourly = []
    await _refresh(hass, entry)

    assert fake_sensus.fetched == []
    assert await _rows(hass) == []

    fake_sensus.hourly = _day_entries(date(2026, 9, 21))
    await _refresh(hass, entry)
    assert len(await _rows(hass)) == (BACKFILL_DAYS + 1) * 24


async def test_backfill_stops_at_first_failed_day_and_retries(hass: HomeAssistant, fake_sensus: FakeSensus) -> None:
    """A failed day keeps the days before it, skips the rest, and the next poll finishes the job."""
    first_day = date(2026, 9, 21) - timedelta(days=BACKFILL_DAYS)
    failing_day = first_day + timedelta(days=3)
    fake_sensus.fail_on = {failing_day}
    entry = await _setup(hass)

    rows = await _rows(hass)
    assert len(rows) == 3 * 24
    assert fake_sensus.fetched[-1] == failing_day

    fake_sensus.fail_on = set()
    fake_sensus.fetched.clear()
    await _refresh(hass, entry)

    assert fake_sensus.fetched[0] == failing_day
    rows = await _rows(hass)
    assert len(rows) == (BACKFILL_DAYS + 1) * 24
    _assert_chained(rows)


async def test_runs_never_overlap(hass: HomeAssistant, fake_sensus: FakeSensus) -> None:
    """A slow backfill is not started again by later polls and direct runs wait for the lock."""
    started = asyncio.Event()
    release = asyncio.Event()
    running = 0
    max_running = 0
    original = fake_sensus.get_hourly_data

    async def slow_get_hourly_data(**kwargs: Any) -> list[dict]:
        nonlocal running, max_running
        running += 1
        max_running = max(max_running, running)
        started.set()
        await release.wait()
        running -= 1
        return await original(**kwargs)

    with patch.object(SensusAnalyticsApiClient, "async_get_hourly_data", AsyncMock(side_effect=slow_get_hourly_data)):
        entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, unique_id="123_456")
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await started.wait()

        importer = entry.runtime_data.statistics
        # A poll during the running import doesn't queue another run
        with patch.object(importer, "async_import", wraps=importer.async_import) as async_import:
            await entry.runtime_data.coordinator.async_refresh()
            assert async_import.call_count == 0
        extra_run = hass.async_create_task(importer.async_import())
        await asyncio.sleep(0)
        assert max_running == 1

        release.set()
        await extra_run
        await _wait(hass)

    assert max_running == 1
    # The backfill ran once; the extra run found nothing new
    assert len(fake_sensus.fetched) == BACKFILL_DAYS
    _assert_chained(await _rows(hass))


async def test_diagnostics_report_last_hour_without_statistic_id(
    hass: HomeAssistant,
    fake_sensus: FakeSensus,
) -> None:
    """Diagnostics show the import progress but not the id, which contains the account and meter."""
    entry = await _setup(hass)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["statistics"] == {
        "unit": UNIT_CCF,
        "last_imported_hour": datetime(2026, 9, 22, 6, tzinfo=UTC).isoformat(),
    }
    assert "123_456" not in str(diagnostics)


# The import_history action

YESTERDAY = date(2026, 9, 21)
# The regular import's first run covers these days
BACKFILL_START = YESTERDAY - timedelta(days=BACKFILL_DAYS)


@pytest.fixture(autouse=True)
def no_delays() -> Generator[None]:
    """Don't wait between requests or before retries."""
    with (
        patch.object(sensus_statistics, "HISTORY_REQUEST_DELAY", 0),
        patch.object(sensus_statistics, "HISTORY_RETRY_DELAY", 0),
    ):
        yield


class FakeSensusHistory(FakeSensus):
    """FakeSensus that can have no data before a day and fail a day a few times."""

    def __init__(self, yesterday: date) -> None:
        """Start with data for every day and no failures."""
        super().__init__(yesterday)
        self.data_since: date | None = None
        self.fail_times: dict[date, int] = {}

    async def get_hourly_data(self, *, target_date: datetime, authenticate: bool = True, **kwargs: Any) -> list[dict]:
        """Return one past day's entries, empty before data_since."""
        day = target_date.date()
        if self.fail_times.get(day):
            self.fetched.append(day)
            self.authenticated.append(authenticate)
            self.fail_times[day] -= 1
            raise SensusAnalyticsApiClientCommunicationError("temporary")
        entries = await super().get_hourly_data(target_date=target_date, authenticate=authenticate, **kwargs)
        if self.data_since is not None and day < self.data_since:
            return []
        return entries


@pytest.fixture
async def sensus(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> Generator[FakeSensusHistory]:
    """Patch the Sensus client with deterministic data for 2026-09-21 as "yesterday"."""
    await hass.config.async_set_time_zone(TIME_ZONE)
    freezer.move_to(datetime(2026, 9, 22, 10, 30, tzinfo=_local_tz()))
    fake = FakeSensusHistory(YESTERDAY)
    with (
        patch.object(SensusAnalyticsApiClient, "async_get_data", AsyncMock(side_effect=fake.get_data)),
        patch.object(SensusAnalyticsApiClient, "async_get_hourly_data", AsyncMock(side_effect=fake.get_hourly_data)),
    ):
        yield fake


def _days(first: date, last: date) -> list[date]:
    """Return every day from first through last."""
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


async def _import_history(hass: HomeAssistant, start_date: str, **data: Any) -> None:
    """Call the action and wait for the background import."""
    await hass.services.async_call(DOMAIN, SERVICE_IMPORT_HISTORY, {"start_date": start_date, **data}, blocking=True)
    await _wait(hass)


@pytest.fixture
def notifications(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    """Collect the persistent notifications created during a test, by notification id."""
    created: dict[str, dict[str, Any]] = {}

    @callback
    def _updated(update_type: persistent_notification.UpdateType, updated: dict[str, Any]) -> None:
        if update_type in (persistent_notification.UpdateType.ADDED, persistent_notification.UpdateType.UPDATED):
            created.update(updated)

    persistent_notification.async_register_callback(hass, _updated)
    return created


async def test_older_history_rebuilds_sums_without_a_jump(
    hass: HomeAssistant,
    sensus: FakeSensusHistory,
    notifications: dict[str, dict[str, Any]],
) -> None:
    """History before the 30-day backfill is imported and every later sum is rebuilt on top of it."""
    entry = await _setup(hass)
    before = await _rows(hass)
    sensus.fetched.clear()
    sensus.authenticated.clear()

    with patch.object(
        sensus_statistics,
        "async_add_external_statistics",
        wraps=sensus_statistics.async_add_external_statistics,
    ) as add_statistics:
        await _import_history(hass, "2026-06-01")

    # Every day up to the one before yesterday is fetched, one login for the whole run
    assert sensus.fetched == _days(date(2026, 6, 1), YESTERDAY - timedelta(days=1))
    assert sensus.authenticated == [True] + [False] * (len(sensus.fetched) - 1)
    rows = await _rows(hass)
    days = _days(date(2026, 6, 1), YESTERDAY)
    assert [row["state"] for row in rows] == pytest.approx([value for day in days for value in _expected_ccf(day)])
    assert rows[0]["start"] == _day_start(date(2026, 6, 1)).timestamp()
    # No jump where the old backfill started: sums chain from the first row to the last
    _assert_chained(rows)
    assert [row["state"] for row in rows[-len(before) :]] == [row["state"] for row in before]
    # Large imports are split into several recorder jobs
    assert add_statistics.call_count == -(-len(rows) // IMPORT_CHUNK_SIZE) > 1

    assert list(notifications) == [f"{DOMAIN}_import_history_{entry.entry_id}"]
    notification = notifications[f"{DOMAIN}_import_history_{entry.entry_id}"]
    assert notification["title"] == "Sensus Analytics history import"
    assert "Imported 113 days" in notification["message"]
    assert "starting June 1, 2026" in notification["message"]
    assert "Sensus Analytics water usage" in notification["message"]
    assert "no hourly data before" not in notification["message"]

    # Rerunning over part of the range keeps earlier hours and continues their sum
    first_rows = rows
    sensus.usage_fn = lambda day, hour: day.day + hour / 10 + 1
    await _import_history(hass, "2026-09-10")
    rows = await _rows(hass)
    split = next(index for index, row in enumerate(rows) if row["start"] >= _day_start(date(2026, 9, 10)).timestamp())
    assert rows[:split] == first_rows[:split]
    assert [row["state"] for row in rows[split:-24]] == pytest.approx(
        [value for day in _days(date(2026, 9, 10), date(2026, 9, 20)) for value in _expected_ccf(day, sensus.usage_fn)],
    )
    _assert_chained(rows)
    # The rerun replaces the notification
    assert list(notifications) == [f"{DOMAIN}_import_history_{entry.entry_id}"]
    assert "Imported 12 days" in notifications[f"{DOMAIN}_import_history_{entry.entry_id}"]["message"]


async def test_leading_days_without_data_are_skipped(
    hass: HomeAssistant,
    sensus: FakeSensusHistory,
    notifications: dict[str, dict[str, Any]],
) -> None:
    """Nothing is written before the first day Sensus has data for, and that day is reported."""
    await _setup(hass)
    sensus.data_since = date(2026, 7, 15)

    await _import_history(hass, "2026-06-01")

    rows = await _rows(hass)
    assert rows[0]["start"] == _day_start(date(2026, 7, 15)).timestamp()
    assert len(rows) == len(_days(date(2026, 7, 15), YESTERDAY)) * 24
    _assert_chained(rows)
    message = next(iter(notifications.values()))["message"]
    assert "Imported 69 days" in message
    assert "starting July 15, 2026" in message
    assert "no hourly data before that day" in message


async def test_no_data_at_all_is_reported(
    hass: HomeAssistant,
    sensus: FakeSensusHistory,
    notifications: dict[str, dict[str, Any]],
) -> None:
    """Without coordinator hourly data the import stops the day before yesterday and says it found nothing."""
    sensus.hourly = None
    await _setup(hass)
    sensus.data_since = YESTERDAY

    await _import_history(hass, "2026-09-01")

    # Yesterday may not be published yet, so it is left to the regular import
    assert sensus.fetched == _days(date(2026, 9, 1), YESTERDAY - timedelta(days=1))
    assert await _rows(hass) == []
    message = next(iter(notifications.values()))["message"]
    assert "no hourly water usage from September 1, 2026 onwards" in message


async def test_failed_day_writes_nothing(
    hass: HomeAssistant,
    sensus: FakeSensusHistory,
    notifications: dict[str, dict[str, Any]],
) -> None:
    """A day that still fails after every retry leaves the statistic untouched."""
    await _setup(hass)
    before = await _rows(hass)
    failing_day = date(2026, 7, 20)
    sensus.fail_on = {failing_day}
    sensus.fetched.clear()

    with patch.object(sensus_statistics, "async_add_external_statistics") as add_statistics:
        await _import_history(hass, "2026-06-01")
        assert add_statistics.call_count == 0

    assert sensus.fetched.count(failing_day) == HISTORY_RETRIES + 1
    # The run stops at the failing day
    assert sensus.fetched[-1] == failing_day
    assert await _rows(hass) == before
    message = next(iter(notifications.values()))["message"]
    assert "nothing was changed" in message
    assert "try again later" in message


async def test_transient_failure_is_retried_with_a_new_login(hass: HomeAssistant, sensus: FakeSensusHistory) -> None:
    """A day that fails twice succeeds on a retry, logging in again first."""
    await _setup(hass)
    flaky_day = date(2026, 8, 10)
    sensus.fail_times = {flaky_day: 2}
    sensus.fetched.clear()
    sensus.authenticated.clear()

    await _import_history(hass, "2026-08-08")

    assert sensus.fetched[:5] == [date(2026, 8, 8), date(2026, 8, 9), flaky_day, flaky_day, flaky_day]
    assert sensus.authenticated[:6] == [True, False, False, True, True, False]
    rows = await _rows(hass)
    assert rows[0]["start"] == _day_start(date(2026, 8, 8)).timestamp()
    assert len(rows) == len(_days(date(2026, 8, 8), YESTERDAY)) * 24
    _assert_chained(rows)


@pytest.mark.parametrize(
    ("hours", "day"),
    [
        # Clocks fall back on 2025-11-02 (25 hours) and spring forward on 2026-03-08 (23 hours)
        (25, date(2025, 11, 2)),
        (23, date(2026, 3, 8)),
    ],
)
async def test_dst_days_in_range_import_every_hour(
    hass: HomeAssistant,
    sensus: FakeSensusHistory,
    hours: int,
    day: date,
) -> None:
    """Days with a DST change inside the range import all of their 23 or 25 hours."""
    await _setup(hass)

    await _import_history(hass, (day - timedelta(days=1)).isoformat())

    rows = await _rows(hass)
    day_rows = [
        row for row in rows if _day_start(day).timestamp() <= row["start"] < _day_start(day + timedelta(1)).timestamp()
    ]
    assert len(day_rows) == hours
    assert [row["state"] for row in day_rows] == pytest.approx(_expected_ccf(day))
    _assert_chained(rows)


@pytest.mark.parametrize(
    ("start_date", "translation_key"),
    [
        ("2026-09-22", "start_date_too_recent"),
        ("2026-10-01", "start_date_too_recent"),
        ("2023-09-21", "start_date_too_old"),
    ],
)
async def test_invalid_start_date(
    hass: HomeAssistant,
    sensus: FakeSensusHistory,
    start_date: str,
    translation_key: str,
) -> None:
    """Today, future dates, and dates more than 3 years ago are rejected."""
    await _setup(hass)
    sensus.fetched.clear()

    with pytest.raises(ServiceValidationError) as error:
        await hass.services.async_call(DOMAIN, SERVICE_IMPORT_HISTORY, {"start_date": start_date}, blocking=True)

    assert error.value.translation_key == translation_key
    await _wait(hass)
    assert sensus.fetched == []


async def test_unknown_or_unloaded_entry(hass: HomeAssistant, sensus: FakeSensusHistory) -> None:
    """An unknown entry id, or no loaded entry at all, is rejected."""
    entry = await _setup(hass)

    with pytest.raises(ServiceValidationError) as error:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_IMPORT_HISTORY,
            {"start_date": "2026-09-01", "config_entry_id": "unknown"},
            blocking=True,
        )
    assert error.value.translation_key == "no_loaded_entry"

    assert await hass.config_entries.async_unload(entry.entry_id)
    with pytest.raises(ServiceValidationError) as error:
        await hass.services.async_call(DOMAIN, SERVICE_IMPORT_HISTORY, {"start_date": "2026-09-01"}, blocking=True)
    assert error.value.translation_key == "no_loaded_entry"


async def test_history_import_blocks_regular_imports_and_reruns(
    hass: HomeAssistant,
    sensus: FakeSensusHistory,
) -> None:
    """While a history import runs, a second one is rejected and regular imports wait without piling up."""
    entry = await _setup(hass)
    importer = entry.runtime_data.statistics
    started = asyncio.Event()
    release = asyncio.Event()
    original = sensus.get_hourly_data

    async def slow_get_hourly_data(**kwargs: Any) -> list[dict]:
        started.set()
        await release.wait()
        return await original(**kwargs)

    with (
        patch.object(SensusAnalyticsApiClient, "async_get_hourly_data", AsyncMock(side_effect=slow_get_hourly_data)),
        patch.object(
            sensus_statistics,
            "async_add_external_statistics",
            wraps=sensus_statistics.async_add_external_statistics,
        ) as add_statistics,
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_IMPORT_HISTORY,
            {"start_date": "2026-09-01", "config_entry_id": entry.entry_id},
            blocking=True,
        )
        await started.wait()
        assert importer.history_import_running

        with pytest.raises(ServiceValidationError) as error:
            await hass.services.async_call(DOMAIN, SERVICE_IMPORT_HISTORY, {"start_date": "2026-09-01"}, blocking=True)
        assert error.value.translation_key == "history_import_running"

        # A correction arrives while the history import runs: one regular run is queued, not one per poll
        sensus.hourly = [{**item, "usage": item["usage"] + 1} for item in _day_entries(YESTERDAY)]
        with patch.object(importer, "async_import", wraps=importer.async_import) as async_import:
            for _ in range(3):
                await entry.runtime_data.coordinator.async_refresh()
            await asyncio.sleep(0)
            assert async_import.call_count == 1
            assert add_statistics.call_count == 0

            release.set()
            await _wait(hass)

        # The history import wrote first, then the waiting regular run imported the correction
        assert not importer.history_import_running
        assert add_statistics.call_count == 2
        history_rows = add_statistics.call_args_list[0].args[2]
        assert history_rows[0]["start"] == _day_start(date(2026, 9, 1))
        correction_rows = add_statistics.call_args_list[1].args[2]
        assert correction_rows[0]["start"] == _day_start(YESTERDAY)

        # Polls with unchanged data don't import again
        await _refresh(hass, entry)
        assert add_statistics.call_count == 2

    rows = await _rows(hass)
    assert rows[-1]["state"] == pytest.approx(_expected_ccf(YESTERDAY)[-1] + 0.01)
    assert rows[0]["start"] == _day_start(BACKFILL_START).timestamp()
    _assert_chained(rows)


async def test_newer_hours_are_rechained_when_yesterday_is_not_fetched(
    hass: HomeAssistant,
    sensus: FakeSensusHistory,
) -> None:
    """Hours after the imported range (here yesterday, from the regular import) get rebuilt sums."""
    entry = await _setup(hass)
    before = await _rows(hass)
    # The coordinator's best-effort hourly fetch failed, so yesterday is left out of the history import
    sensus.hourly = None
    await _refresh(hass, entry)

    await _import_history(hass, "2026-08-01")

    assert sensus.fetched[-1] == YESTERDAY - timedelta(days=1)
    rows = await _rows(hass)
    assert rows[0]["start"] == _day_start(date(2026, 8, 1)).timestamp()
    assert [row["state"] for row in rows[-24:]] == [row["state"] for row in before[-24:]]
    _assert_chained(rows)
