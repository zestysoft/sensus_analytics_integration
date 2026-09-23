"""Set up the Sensus Analytics integration."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import aiohttp

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.helpers.aiohttp_client import async_create_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.loader import async_get_loaded_integration

from .api import SensusAnalyticsApiClient
from .const import CONF_BASE_URL, CONF_UPDATE_INTERVAL_MINUTES, DEFAULT_UPDATE_INTERVAL_MINUTES, DOMAIN, LOGGER
from .coordinator import SensusAnalyticsDataUpdateCoordinator
from .data import SensusAnalyticsData, get_config_value
from .service_actions import async_setup_services

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import SensusAnalyticsConfigEntry

PLATFORMS: list[Platform] = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Sensus Analytics services."""
    await async_setup_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SensusAnalyticsConfigEntry,
) -> bool:
    """Set up Sensus Analytics from a config entry."""
    client = SensusAnalyticsApiClient(
        base_url=entry.data[CONF_BASE_URL],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        # Sensus keeps the login in a session cookie, so each entry needs its own cookie jar.
        # Home Assistant detaches this session automatically when the entry is unloaded.
        session=async_create_clientsession(hass, cookie_jar=aiohttp.CookieJar()),
    )

    coordinator = SensusAnalyticsDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        config_entry=entry,
        update_interval=timedelta(
            minutes=get_config_value(
                entry,
                CONF_UPDATE_INTERVAL_MINUTES,
                DEFAULT_UPDATE_INTERVAL_MINUTES,
            ),
        ),
    )

    entry.runtime_data = SensusAnalyticsData(
        client=client,
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    await coordinator.async_config_entry_first_refresh()

    # No update listener: the options flow and the reauth/reconfigure flows each schedule a single reload
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: SensusAnalyticsConfigEntry,
) -> bool:
    """Unload a Sensus Analytics config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
