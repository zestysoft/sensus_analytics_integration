"""Tests for Sensus Analytics sensor descriptions."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.sensus_analytics.const import (
    CONF_SERVICE_FEE,
    CONF_TIER1_GALLONS,
    CONF_TIER1_PRICE,
    CONF_TIER2_PRICE,
    CONF_UNIT_TYPE,
    UNIT_CCF,
    UNIT_GALLONS,
)
from custom_components.sensus_analytics.sensor.water import ENTITY_DESCRIPTIONS


def _description(key: str):
    """Return a sensor entity description by key."""
    return next(description for description in ENTITY_DESCRIPTIONS if description.key == key)


def _coordinator(data: dict, config_data: dict, options: dict | None = None):
    """Return a minimal coordinator-like object for value function tests."""
    return SimpleNamespace(
        data=data,
        config_entry=SimpleNamespace(data=config_data, options=options or {}),
        hass=SimpleNamespace(config=SimpleNamespace(currency="USD", time_zone="America/Los_Angeles")),
    )


def test_daily_usage_converts_cubic_feet_to_gallons() -> None:
    """Daily usage uses the configured display unit."""
    coordinator = _coordinator(
        {"dailyUsage": 10, "usageUnit": "CF"},
        {CONF_UNIT_TYPE: UNIT_GALLONS},
    )

    assert _description("daily_usage").value_fn(coordinator) == 75
    assert _description("daily_usage").unit_fn(coordinator) == "gal"


def test_billing_cost_prices_gallons_when_displaying_gallons() -> None:
    """Billing cost prices usage in gallons when the display unit is gallons."""
    coordinator = _coordinator(
        {"billingUsage": 100, "usageUnit": "CF"},
        {
            CONF_UNIT_TYPE: UNIT_GALLONS,
            CONF_TIER1_PRICE: 0.01,
            CONF_SERVICE_FEE: 15.0,
        },
    )

    # 100 CF displays as 748 gal
    assert _description("billing_cost").value_fn(coordinator) == 22.48


def test_billing_cost_prices_ccf_when_displaying_ccf() -> None:
    """Billing cost prices usage in CCF when the display unit is CCF."""
    coordinator = _coordinator(
        {"billingUsage": 500, "usageUnit": "CF"},
        {
            CONF_UNIT_TYPE: UNIT_CCF,
            CONF_TIER1_PRICE: 4.0,
            CONF_SERVICE_FEE: 15.0,
        },
    )

    # 500 CF displays as 5 CCF: 5 * 4.00 + 15.00
    assert _description("billing_cost").value_fn(coordinator) == 35.0


def test_daily_fee_applies_tiers_in_display_unit() -> None:
    """Tier limits are in the display unit and the daily fee excludes the service fee."""
    coordinator = _coordinator(
        {"dailyUsage": 300, "usageUnit": "CF"},
        {
            CONF_UNIT_TYPE: UNIT_CCF,
            CONF_TIER1_GALLONS: 2,
            CONF_TIER1_PRICE: 4.0,
            CONF_TIER2_PRICE: 6.0,
            CONF_SERVICE_FEE: 15.0,
        },
    )

    # 300 CF displays as 3 CCF: 2 * 4.00 + 1 * 6.00
    assert _description("daily_fee").value_fn(coordinator) == 14.0
