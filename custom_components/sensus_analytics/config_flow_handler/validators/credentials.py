"""Credential validation for Sensus Analytics config flow."""

from __future__ import annotations

from typing import Any

from custom_components.sensus_analytics.api import SensusAnalyticsApiClient
from custom_components.sensus_analytics.const import CONF_BASE_URL
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .sanitizers import sanitize_config_input


async def validate_credentials(
    hass: HomeAssistant,
    user_input: dict[str, Any],
) -> dict[str, Any]:
    """Validate credentials and return sanitized user input."""
    sanitized = sanitize_config_input(user_input)
    client = SensusAnalyticsApiClient(
        base_url=sanitized[CONF_BASE_URL],
        username=sanitized[CONF_USERNAME],
        password=sanitized[CONF_PASSWORD],
        session=async_get_clientsession(hass),
    )
    await client.async_authenticate()
    return sanitized


__all__ = ["validate_credentials"]
