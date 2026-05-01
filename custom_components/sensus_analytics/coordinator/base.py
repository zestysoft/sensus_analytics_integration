"""DataUpdateCoordinator implementation for Sensus Analytics."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from custom_components.sensus_analytics.api import (
    SensusAnalyticsApiClientAuthenticationError,
    SensusAnalyticsApiClientError,
)
from custom_components.sensus_analytics.const import CONF_ACCOUNT_NUMBER, CONF_METER_NUMBER, DOMAIN, LOGGER
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from custom_components.sensus_analytics.data import SensusAnalyticsConfigEntry


class SensusAnalyticsDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage Sensus Analytics data fetching."""

    config_entry: SensusAnalyticsConfigEntry

    async def _async_setup(self) -> None:
        """Set up the coordinator before the first refresh."""
        LOGGER.debug("Coordinator setup complete for %s", self.config_entry.entry_id)

    async def _async_update_data(self) -> Any:
        """Fetch data from Sensus Analytics."""
        local_tz = dt_util.get_time_zone(self.hass.config.time_zone) or dt_util.DEFAULT_TIME_ZONE
        target_date = datetime.now(local_tz) - timedelta(days=1)

        try:
            return await self.config_entry.runtime_data.client.async_get_data(
                account_number=self.config_entry.data[CONF_ACCOUNT_NUMBER],
                meter_number=self.config_entry.data[CONF_METER_NUMBER],
                target_date=target_date,
            )
        except SensusAnalyticsApiClientAuthenticationError as exception:
            LOGGER.warning("Authentication error - %s", exception)
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="authentication_failed",
            ) from exception
        except SensusAnalyticsApiClientError as exception:
            LOGGER.exception("Error communicating with Sensus Analytics")
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
            ) from exception
