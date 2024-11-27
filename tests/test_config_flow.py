"""Test the config flow for Sensus Analytics Integration."""

from unittest.mock import patch

from homeassistant import config_entries, setup
from homeassistant.core import HomeAssistant

from custom_components.sensus_analytics.const import DOMAIN


async def test_form_success(hass: HomeAssistant):
    """Test successful config flow."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"  # nosec B101
    assert result["errors"] == {}  # nosec B101

    with patch(
        "custom_components.sensus_analytics.config_flow.validate_input",
        return_value={"title": "Sensus Analytics"},
    ), patch(
        "custom_components.sensus_analytics.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
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
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"  # nosec B101
    assert result2["title"] == "Sensus Analytics"  # nosec B101
    assert result2["data"] == {
        "base_url": "https://example.com",
        "username": "user",
        "password": "pass",
        "account_number": "123456",
        "meter_number": "7890",
    }  # nosec B101

    # Ensure the config entry was set up
    assert len(mock_setup_entry.mock_calls) == 1  # nosec B101
