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
    }
