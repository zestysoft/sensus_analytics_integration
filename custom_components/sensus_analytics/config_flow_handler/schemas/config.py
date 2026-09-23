"""Config flow schemas for Sensus Analytics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from custom_components.sensus_analytics.const import (
    CONF_ACCOUNT_NUMBER,
    CONF_BASE_URL,
    CONF_METER_NUMBER,
    CONF_SERVICE_FEE,
    CONF_TIER1_GALLONS,
    CONF_TIER1_PRICE,
    CONF_TIER2_GALLONS,
    CONF_TIER2_PRICE,
    CONF_TIER3_PRICE,
    CONF_UNIT_TYPE,
    DEFAULT_SERVICE_FEE,
    DEFAULT_TIER1_PRICE,
    DEFAULT_UNIT_TYPE,
    UNIT_CCF,
    UNIT_GALLONS,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector

_NON_NEGATIVE_FLOAT = vol.All(vol.Coerce(float), vol.Range(min=0))


def _text_selector(password: bool = False) -> selector.TextSelector:
    """Return a text selector."""
    return selector.TextSelector(
        selector.TextSelectorConfig(
            type=selector.TextSelectorType.PASSWORD if password else selector.TextSelectorType.TEXT,
        ),
    )


def _number_key(key: str, defaults: Mapping[str, Any], *, required: bool, default: float | None = None) -> vol.Marker:
    """Return a voluptuous marker for a numeric field."""
    configured_default = defaults.get(key, default)
    marker = vol.Required if required else vol.Optional
    if configured_default is None:
        return marker(key)
    return marker(key, default=configured_default)


def get_user_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Get schema for the initial setup step."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_BASE_URL,
                default=defaults.get(CONF_BASE_URL, vol.UNDEFINED),
            ): _text_selector(),
            vol.Required(
                CONF_USERNAME,
                default=defaults.get(CONF_USERNAME, vol.UNDEFINED),
            ): _text_selector(),
            vol.Required(CONF_PASSWORD): _text_selector(password=True),
            vol.Required(
                CONF_ACCOUNT_NUMBER,
                default=defaults.get(CONF_ACCOUNT_NUMBER, vol.UNDEFINED),
            ): _text_selector(),
            vol.Required(
                CONF_METER_NUMBER,
                default=defaults.get(CONF_METER_NUMBER, vol.UNDEFINED),
            ): _text_selector(),
            vol.Required(CONF_UNIT_TYPE, default=defaults.get(CONF_UNIT_TYPE, DEFAULT_UNIT_TYPE)): vol.In(
                [UNIT_CCF, UNIT_GALLONS],
            ),
            _number_key(CONF_TIER1_GALLONS, defaults, required=False): _NON_NEGATIVE_FLOAT,
            _number_key(CONF_TIER1_PRICE, defaults, required=True, default=DEFAULT_TIER1_PRICE): _NON_NEGATIVE_FLOAT,
            _number_key(CONF_TIER2_GALLONS, defaults, required=False): _NON_NEGATIVE_FLOAT,
            _number_key(CONF_TIER2_PRICE, defaults, required=False): _NON_NEGATIVE_FLOAT,
            _number_key(CONF_TIER3_PRICE, defaults, required=False): _NON_NEGATIVE_FLOAT,
            _number_key(CONF_SERVICE_FEE, defaults, required=True, default=DEFAULT_SERVICE_FEE): _NON_NEGATIVE_FLOAT,
        },
    )


def get_reconfigure_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    """Get schema for reconfiguration."""
    return get_user_schema(defaults)


def get_reauth_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    """Get schema for reauthentication."""
    return vol.Schema(
        {
            vol.Required(
                CONF_USERNAME,
                default=defaults.get(CONF_USERNAME, vol.UNDEFINED),
            ): _text_selector(),
            vol.Required(CONF_PASSWORD): _text_selector(password=True),
        },
    )


__all__ = [
    "get_reauth_schema",
    "get_reconfigure_schema",
    "get_user_schema",
]
