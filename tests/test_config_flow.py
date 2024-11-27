"""Test the config flow for Sensus Analytics Integration."""
from unittest.mock import patch

from homeassistant import config_entries, setup
from homeassistant.core import HomeAssistant

from custom_components.sensus_analytics.const import DOMAIN

async def test_form(hass: HomeAssistant):
    """Test we can setup by config flow."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "custom_components.sensus_analytics.config_flow.SensusAnalyticsConfigFlow.async_create_entry",
        return_value={"title": "Sensus Analytics", "data": {}}
    ) as mock_create_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "base_url": "https://example.com",
                "username": "user",
                "password": "pass",
                "account_number": "123456",
                "meter_number": "7890",
            },
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Sensus Analytics"
    assert result2["data"] == {
        "base_url": "https://example.com",
        "username": "user",
        "password": "pass",
        "account_number": "123456",
        "meter_number": "7890",
    }
