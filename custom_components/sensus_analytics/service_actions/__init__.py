"""Service actions for Sensus Analytics."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from custom_components.sensus_analytics.const import DOMAIN, LOGGER, SERVICE_RELOAD_DATA

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for the integration."""

    async def handle_reload_data(call: ServiceCall) -> None:
        """Manually trigger data refresh for all loaded entries."""
        LOGGER.debug("Manual data reload requested")

        refresh_tasks = [
            entry.runtime_data.coordinator.async_request_refresh()
            for entry in hass.config_entries.async_entries(DOMAIN)
            if getattr(entry, "runtime_data", None)
        ]

        if refresh_tasks:
            await asyncio.gather(*refresh_tasks)
            LOGGER.debug("Manual data reload completed for %d entries", len(refresh_tasks))

    hass.services.async_register(
        DOMAIN,
        SERVICE_RELOAD_DATA,
        handle_reload_data,
    )
