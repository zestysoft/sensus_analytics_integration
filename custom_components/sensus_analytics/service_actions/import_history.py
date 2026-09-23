"""The import_history action: import older hourly water usage into the Energy statistic.

The action validates its input, then runs one import per config entry in the background and
reports the outcome with a persistent notification, because a multi-year import makes one
Sensus request per day and can take several minutes.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import voluptuous as vol

from custom_components.sensus_analytics.const import ATTR_START_DATE, DOMAIN, HISTORY_IMPORT_MAX_YEARS, LOGGER
from custom_components.sensus_analytics.statistics import SensusAnalyticsHistoryImportError
from homeassistant.components import persistent_notification
from homeassistant.const import ATTR_CONFIG_ENTRY_ID
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from custom_components.sensus_analytics.data import SensusAnalyticsConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall

IMPORT_HISTORY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_START_DATE): cv.date,
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    },
)
NOTIFICATION_TITLE = "Sensus Analytics history import"


def notification_id(entry: SensusAnalyticsConfigEntry) -> str:
    """Return the notification id for an entry, so a rerun replaces the previous result."""
    return f"{DOMAIN}_import_history_{entry.entry_id}"


def earliest_start_date(today: date) -> date:
    """Return the oldest start date the action accepts."""
    try:
        return today.replace(year=today.year - HISTORY_IMPORT_MAX_YEARS)
    except ValueError:  # February 29
        return today.replace(year=today.year - HISTORY_IMPORT_MAX_YEARS, day=28)


def _format_day(day: date) -> str:
    """Return a day as, for example, September 1, 2025."""
    return f"{day:%B} {day.day}, {day.year}"


async def async_handle_import_history(call: ServiceCall) -> None:
    """Validate the request and start a background history import for each matching entry."""
    hass = call.hass
    start_date: date = call.data[ATTR_START_DATE]
    today = dt_util.now().date()
    if start_date >= today:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="start_date_too_recent",
            translation_placeholders={"latest": (today - timedelta(days=1)).isoformat()},
        )
    earliest = earliest_start_date(today)
    if start_date < earliest:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="start_date_too_old",
            translation_placeholders={"earliest": earliest.isoformat(), "years": str(HISTORY_IMPORT_MAX_YEARS)},
        )

    entries: list[SensusAnalyticsConfigEntry] = hass.config_entries.async_loaded_entries(DOMAIN)
    if entry_id := call.data.get(ATTR_CONFIG_ENTRY_ID):
        entries = [entry for entry in entries if entry.entry_id == entry_id]
    if not entries:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_loaded_entry")
    # Check every entry before starting any, so a rejected call starts nothing
    for entry in entries:
        if entry.runtime_data.statistics.history_import_running:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="history_import_running",
                translation_placeholders={"title": entry.title},
            )

    for entry in entries:
        LOGGER.debug("Starting history import for %s from %s", entry.title, start_date)
        entry.runtime_data.statistics.async_start_history_import(_async_import_and_notify(hass, entry, start_date))


async def _async_import_and_notify(hass: HomeAssistant, entry: SensusAnalyticsConfigEntry, start_date: date) -> None:
    """Run one entry's history import and report the outcome."""
    importer = entry.runtime_data.statistics
    name = importer.statistic_name
    try:
        result = await importer.async_import_history(start_date)
    except SensusAnalyticsHistoryImportError as exception:
        LOGGER.warning("History import for %s failed, nothing was changed: %s", entry.title, exception)
        message = _failure_message(name)
    except Exception:  # noqa: BLE001 - the user is waiting for a notification either way
        LOGGER.exception("Unexpected error importing history for %s", entry.title)
        message = _failure_message(name)
    else:
        if result.first_day is None:
            message = (
                f"Sensus Analytics had no hourly water usage from {_format_day(start_date)} onwards, "
                f"so nothing was added to **{name}**."
            )
        else:
            days = "1 day" if result.days == 1 else f"{result.days} days"
            message = (
                f"Imported {days} of hourly water usage into **{name}**, starting {_format_day(result.first_day)}."
            )
            if result.first_day > start_date:
                message += " Sensus Analytics had no hourly data before that day."
            message += " Energy dashboard totals stay correct, and running the import again is safe."

    persistent_notification.async_create(
        hass, message, title=NOTIFICATION_TITLE, notification_id=notification_id(entry)
    )


def _failure_message(name: str) -> str:
    """Return the notification text for a failed import."""
    return (
        "Couldn't download all of the requested history from Sensus Analytics, so nothing was changed in "
        f"**{name}**. Please try again later."
    )
