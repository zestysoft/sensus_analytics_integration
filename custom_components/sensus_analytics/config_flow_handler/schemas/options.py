"""Options flow schemas for Sensus Analytics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from custom_components.sensus_analytics.const import (
    CONF_SERVICE_FEE,
    CONF_TIER1_GALLONS,
    CONF_TIER1_PRICE,
    CONF_TIER2_GALLONS,
    CONF_TIER2_PRICE,
    CONF_TIER3_PRICE,
    CONF_UNIT_TYPE,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_SERVICE_FEE,
    DEFAULT_TIER1_PRICE,
    DEFAULT_UNIT_TYPE,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    UNIT_CCF,
    UNIT_GALLONS,
)
from homeassistant.helpers import config_validation as cv

_NON_NEGATIVE_FLOAT = vol.All(vol.Coerce(float), vol.Range(min=0))


def _number_key(key: str, defaults: Mapping[str, Any], *, required: bool, default: float | None = None) -> vol.Marker:
    """Return a marker for an option number."""
    configured_default = defaults.get(key, default)
    marker = vol.Required if required else vol.Optional
    if configured_default is None:
        return marker(key)
    return marker(key, default=configured_default)


def get_options_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Get schema for options flow."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_UNIT_TYPE, default=defaults.get(CONF_UNIT_TYPE, DEFAULT_UNIT_TYPE)): vol.In(
                [UNIT_CCF, UNIT_GALLONS],
            ),
            _number_key(CONF_TIER1_GALLONS, defaults, required=False): _NON_NEGATIVE_FLOAT,
            _number_key(CONF_TIER1_PRICE, defaults, required=True, default=DEFAULT_TIER1_PRICE): _NON_NEGATIVE_FLOAT,
            _number_key(CONF_TIER2_GALLONS, defaults, required=False): _NON_NEGATIVE_FLOAT,
            _number_key(CONF_TIER2_PRICE, defaults, required=False): _NON_NEGATIVE_FLOAT,
            _number_key(CONF_TIER3_PRICE, defaults, required=False): _NON_NEGATIVE_FLOAT,
            _number_key(CONF_SERVICE_FEE, defaults, required=True, default=DEFAULT_SERVICE_FEE): _NON_NEGATIVE_FLOAT,
            vol.Required(
                CONF_UPDATE_INTERVAL_MINUTES,
                default=defaults.get(CONF_UPDATE_INTERVAL_MINUTES, DEFAULT_UPDATE_INTERVAL_MINUTES),
            ): vol.All(cv.positive_int, vol.Range(min=1, max=1440)),
        },
    )


__all__ = ["get_options_schema"]
