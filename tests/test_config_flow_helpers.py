"""Tests for config flow helper functions."""

from __future__ import annotations

from custom_components.sensus_analytics.config_flow_handler.schemas import get_options_schema
from custom_components.sensus_analytics.config_flow_handler.validators import sanitize_config_input
from custom_components.sensus_analytics.const import (
    CONF_ACCOUNT_NUMBER,
    CONF_BASE_URL,
    CONF_METER_NUMBER,
    CONF_UPDATE_INTERVAL_MINUTES,
)


def test_sanitize_config_input_normalizes_url_and_identifiers() -> None:
    """Input sanitization trims identifiers and normalizes base URL."""
    sanitized = sanitize_config_input(
        {
            CONF_BASE_URL: "city.sensus-analytics.com///",
            CONF_ACCOUNT_NUMBER: " 123 ",
            CONF_METER_NUMBER: " 456 ",
        },
    )

    assert sanitized[CONF_BASE_URL] == "https://city.sensus-analytics.com/"
    assert sanitized[CONF_ACCOUNT_NUMBER] == "123"
    assert sanitized[CONF_METER_NUMBER] == "456"


def test_options_schema_accepts_update_interval() -> None:
    """Options schema accepts the blueprint-style update interval option."""
    schema = get_options_schema()

    data = schema(
        {
            "unit_type": "gal",
            "tier1_price": 0.01,
            "service_fee": 0,
            CONF_UPDATE_INTERVAL_MINUTES: 15,
        },
    )

    assert data[CONF_UPDATE_INTERVAL_MINUTES] == 15
