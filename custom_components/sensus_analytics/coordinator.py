"""DataUpdateCoordinator for Sensus Analytics Integration."""

import logging
from datetime import timedelta

import requests
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from requests.exceptions import RequestException

from .const import CONF_ACCOUNT_NUMBER, CONF_BASE_URL, CONF_METER_NUMBER, CONF_PASSWORD, CONF_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SensusAnalyticsDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, config_entry):
        """Initialize."""
        self.base_url = config_entry.data[CONF_BASE_URL]
        self.username = config_entry.data[CONF_USERNAME]
        self.password = config_entry.data[CONF_PASSWORD]
        self.account_number = config_entry.data[CONF_ACCOUNT_NUMBER]
        self.meter_number = config_entry.data[CONF_METER_NUMBER]

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )

    async def _async_update_data(self):
        """Fetch data from API."""
        return await self.hass.async_add_executor_job(self._fetch_data)

    def _fetch_data(self):
        """Fetch data from the Sensus Analytics API."""
        try:
            session = requests.Session()
            # Get session cookie
            r_sec = session.post(
                f"{self.base_url}/j_spring_security_check",
                data={"j_username": self.username, "j_password": self.password},
                allow_redirects=False,
                timeout=10,
            )
            # Check if login was successful
            if r_sec.status_code != 302:
                _LOGGER.error("Authentication failed")
                raise UpdateFailed("Authentication failed")

            # Request meter data
            response = session.post(
                f"{self.base_url}/water/widget/byPage",
                json={
                    "group": "meters",
                    "accountNumber": self.account_number,
                    "deviceId": self.meter_number,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json().get("widgetList")[0].get("data").get("devices")[0]
            return data

        except RequestException as error:
            _LOGGER.error("Error fetching data: %s", error)
            raise UpdateFailed(f"Error fetching data: {error}") from error
