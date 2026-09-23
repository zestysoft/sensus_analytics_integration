"""Diagnostics support for Sensus Analytics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import CONF_ACCOUNT_NUMBER, CONF_BASE_URL, CONF_METER_NUMBER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import SensusAnalyticsConfigEntry


TO_REDACT = {
    CONF_ACCOUNT_NUMBER,
    CONF_BASE_URL,
    CONF_METER_NUMBER,
    CONF_PASSWORD,
    CONF_USERNAME,
    "meterAddress1",
    "meterId",
    "meterLat",
    "meterLong",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: SensusAnalyticsConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    statistics = entry.runtime_data.statistics
    last_imported_hour = await statistics.async_get_last_imported_hour()
    return {
        "entry": async_redact_data(
            {
                "data": dict(entry.data),
                "options": dict(entry.options),
                "entry_id": entry.entry_id,
                "state": entry.state.name if entry.state else None,
            },
            TO_REDACT,
        ),
        "coordinator_data": async_redact_data(entry.runtime_data.coordinator.data or {}, TO_REDACT),
        # The statistic id contains the account and meter numbers, so only the unit is reported
        "statistics": {
            "unit": statistics.unit,
            "last_imported_hour": last_imported_hour.isoformat() if last_imported_hour else None,
        },
    }
