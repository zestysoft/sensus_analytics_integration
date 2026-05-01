"""Tests for Sensus Analytics sensor descriptions."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.sensus_analytics.const import CONF_SERVICE_FEE, CONF_TIER1_PRICE, CONF_UNIT_TYPE, UNIT_GALLONS
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


def test_billing_cost_uses_gallons_for_pricing() -> None:
    """Billing cost pricing is calculated in gallons."""
    coordinator = _coordinator(
        {"billingUsage": 100, "usageUnit": "CF"},
        {
            CONF_UNIT_TYPE: UNIT_GALLONS,
            CONF_TIER1_PRICE: 0.01,
            CONF_SERVICE_FEE: 15.0,
        },
    )

    assert _description("billing_cost").value_fn(coordinator) == 22.48
