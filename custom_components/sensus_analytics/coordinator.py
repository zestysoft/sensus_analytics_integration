"""DataUpdateCoordinator for Sensus Analytics Integration."""

import logging
from datetime import datetime, timedelta
from urllib.parse import urljoin  # Import urljoin

import requests
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util  # Import HA's datetime utilities

from .const import CONF_ACCOUNT_NUMBER, CONF_BASE_URL, CONF_METER_NUMBER, CONF_PASSWORD, CONF_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SensusAnalyticsDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, config_entry):
        """Initialize."""
        self.hass = hass
        self.base_url = config_entry.data[CONF_BASE_URL]
        self.username = config_entry.data[CONF_USERNAME]
        self.password = config_entry.data[CONF_PASSWORD]
        self.account_number = config_entry.data[CONF_ACCOUNT_NUMBER]
        self.meter_number = config_entry.data[CONF_METER_NUMBER]
        self.config_entry = config_entry

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )

    async def _async_update_data(self):
        """Fetch data from API."""
        _LOGGER.debug("Async update of data started")
        return await self.hass.async_add_executor_job(self._fetch_data)

    def _fetch_data(self):
        """Fetch data from the Sensus Analytics API."""
        _LOGGER.debug("Starting data fetch from Sensus Analytics API")
        try:
            session = self._create_authenticated_session()

            # Fetch daily data
            data = self._fetch_daily_data(session)

            # Fetch hourly data
            _LOGGER.debug("Fetching hourly data")
            local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
            now_local = datetime.now(local_tz)
            target_date = now_local - timedelta(days=1)
            hourly_data = self._retrieve_hourly_data(session, target_date)
            if hourly_data:
                data["hourly_usage_data"] = hourly_data
            else:
                _LOGGER.warning("Failed to fetch hourly data")

            return data

        except UpdateFailed as error:
            raise error
        except Exception as error:
            _LOGGER.error("Unexpected error: %s", error)
            raise UpdateFailed(f"Unexpected error: {error}") from error

    def _create_authenticated_session(self):
        """Create and return an authenticated session."""
        session = requests.Session()
        # Authenticate and get session cookie
        login_url = urljoin(self.base_url, "j_spring_security_check")
        _LOGGER.debug("Authentication URL: %s", login_url)
        r_sec = session.post(
            login_url,
            data={"j_username": self.username, "j_password": self.password},
            allow_redirects=False,
            timeout=10,
        )
        # Check if login was successful
        if r_sec.status_code != 302:
            _LOGGER.error("Authentication failed with status code %s", r_sec.status_code)
            raise UpdateFailed("Authentication failed")

        _LOGGER.debug("Authentication successful")
        return session

    def _fetch_daily_data(self, session):
        """Fetch daily meter data."""
        widget_url = urljoin(self.base_url, "water/widget/byPage")
        _LOGGER.debug("Widget URL: %s", widget_url)
        response = session.post(
            widget_url,
            json={
                "group": "meters",
                "accountNumber": self.account_number,
                "deviceId": self.meter_number,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        _LOGGER.debug("Raw response data: %s", data)
        # Navigate to the specific data
        data = data.get("widgetList")[0].get("data").get("devices")[0]
        _LOGGER.debug("Parsed data: %s", data)
        return data

    def _retrieve_hourly_data(self, session: requests.Session, target_date: datetime):
        """Retrieve hourly usage data for a specific date based on local time."""
        # Prepare request parameters
        start_ts, end_ts = self._get_start_end_timestamps(target_date)
        usage_url, params = self._construct_hourly_data_request(start_ts, end_ts)

        _LOGGER.debug("Hourly data request URL: %s", usage_url)
        _LOGGER.debug("Hourly data request parameters: %s", params)

        try:
            response = session.get(usage_url, params=params, timeout=10)
            response.raise_for_status()  # Ensure the request was successful
            hourly_data = response.json()
            _LOGGER.debug("Hourly data response: %s", hourly_data)

            # Validate and process the response
            hourly_entries = self._process_hourly_data_response(hourly_data)
            return hourly_entries

        except requests.exceptions.RequestException as e:
            _LOGGER.error("Hourly data retrieval failed: %s", e)
            return None
        except (KeyError, TypeError, ValueError) as e:
            _LOGGER.error("Error processing the hourly data response: %s", e)
            return None

    def _get_start_end_timestamps(self, target_date):
        """Get start and end timestamps in milliseconds for the target date."""
        # Use HA's local timezone
        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)

        # Start and end of the day in local time with timezone
        start_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=local_tz)
        end_dt = datetime.combine(target_date, datetime.max.time(), tzinfo=local_tz)

        # Convert to timestamps in milliseconds
        start_ts = int(start_dt.timestamp() * 1000)
        end_ts = int(end_dt.timestamp() * 1000)
        return start_ts, end_ts

    def _construct_hourly_data_request(self, start_ts, end_ts):
        """Construct the hourly data request URL and parameters."""
        usage_url = urljoin(self.base_url, f"water/usage/{self.account_number}/{self.meter_number}")
        params = {
            "start": start_ts,
            "end": end_ts,
            "zoom": "day",
            "page": "null",
            "weather": "1",
        }
        return usage_url, params

    def _process_hourly_data_response(self, hourly_data):
        """Process and structure the hourly data response."""
        if not isinstance(hourly_data, dict):
            _LOGGER.error("Unexpected response format for hourly data.")
            return None

        if not hourly_data.get("operationSuccess", False):
            errors = hourly_data.get("errors", [])
            _LOGGER.error("API returned errors: %s", errors)
            return None

        usage_list = hourly_data.get("data", {}).get("usage", [])
        if not usage_list or len(usage_list) < 2:
            _LOGGER.error("Hourly usage data is missing or incomplete.")
            return None

        # The first element contains units
        units = usage_list[0]  # ["CF", "INCHES", "FAHRENHEIT", "CF"]
        usage_unit = units[0]
        rain_unit = units[1]
        temp_unit = units[2]

        # The rest of the list contains hourly data
        hourly_entries = []
        for entry in usage_list[1:]:
            timestamp, usage, rain, temp = entry[:4]
            hourly_entries.append(
                {
                    "timestamp": timestamp,
                    "usage": usage,
                    "rain": rain,
                    "temp": temp,
                    "usage_unit": usage_unit,
                    "rain_unit": rain_unit,
                    "temp_unit": temp_unit,
                }
            )

        return hourly_entries
