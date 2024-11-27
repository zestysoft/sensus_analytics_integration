"""Test the Sensus Analytics sensor."""
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState

from custom_components.sensus_analytics.const import DOMAIN

async def test_sensor(hass: HomeAssistant):
    """Test sensor setup."""
    config_entry = hass.config_entries.async_entries(DOMAIN)[0]

    with patch(
        "custom_components.sensus_analytics.coordinator.SensusAnalyticsDataUpdateCoordinator._fetch_data",
        return_value={
            "dailyUsage": 18.0,
            "usageUnit": "CF",
            "meterId": "79071217",
            # Add other data as needed
        },
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.sensus_analytics_usage")
    assert state is not None
    assert state.state == "18.0"
