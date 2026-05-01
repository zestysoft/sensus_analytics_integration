"""Async API client for Sensus Analytics."""

from __future__ import annotations

from datetime import datetime, time
import socket
from typing import Any, NoReturn
from urllib.parse import urljoin

import aiohttp

from custom_components.sensus_analytics.const import LOGGER
from homeassistant.util import dt as dt_util


class SensusAnalyticsApiClientError(Exception):
    """Base exception for Sensus Analytics API errors."""


class SensusAnalyticsApiClientCommunicationError(SensusAnalyticsApiClientError):
    """Exception for communication errors."""


class SensusAnalyticsApiClientAuthenticationError(SensusAnalyticsApiClientError):
    """Exception for authentication errors."""


def _raise_authentication_error(message: str) -> NoReturn:
    """Raise an authentication error."""
    raise SensusAnalyticsApiClientAuthenticationError(message)


class SensusAnalyticsApiClient:
    """Client for the Sensus Analytics web endpoints used by the integration."""

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the API client."""
        self._base_url = base_url.rstrip("/") + "/"
        self._username = username
        self._password = password
        self._session = session

    async def async_authenticate(self) -> None:
        """Authenticate the shared client session against Sensus Analytics."""
        try:
            async with self._session.post(
                self._url("j_spring_security_check"),
                data={
                    "j_username": self._username,
                    "j_password": self._password,
                },
                allow_redirects=False,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 302:
                    _raise_authentication_error(
                        f"Authentication failed with status {response.status}",
                    )
        except SensusAnalyticsApiClientAuthenticationError:
            raise
        except (TimeoutError, aiohttp.ClientError, socket.gaierror) as exception:
            raise SensusAnalyticsApiClientCommunicationError(
                f"Authentication request failed: {exception}",
            ) from exception

    async def async_get_data(
        self,
        *,
        account_number: str,
        meter_number: str,
        target_date: datetime,
    ) -> dict[str, Any]:
        """Authenticate and fetch daily plus best-effort hourly meter data."""
        await self.async_authenticate()
        daily_data = await self._async_get_daily_data(account_number, meter_number)

        try:
            hourly_data = await self._async_get_hourly_data(
                account_number=account_number,
                meter_number=meter_number,
                target_date=target_date,
            )
        except SensusAnalyticsApiClientCommunicationError as exception:
            LOGGER.warning("Failed to fetch Sensus hourly data: %s", exception)
        else:
            daily_data["hourly_usage_data"] = hourly_data

        return daily_data

    async def _async_get_daily_data(
        self,
        account_number: str,
        meter_number: str,
    ) -> dict[str, Any]:
        """Fetch daily meter data."""
        try:
            async with self._session.post(
                self._url("water/widget/byPage"),
                json={
                    "group": "meters",
                    "accountNumber": account_number,
                    "deviceId": meter_number,
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status in (401, 403):
                    _raise_authentication_error(
                        f"Daily data request failed with status {response.status}",
                    )
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except SensusAnalyticsApiClientAuthenticationError:
            raise
        except (TimeoutError, aiohttp.ClientError, socket.gaierror) as exception:
            raise SensusAnalyticsApiClientCommunicationError(
                f"Daily data request failed: {exception}",
            ) from exception

        try:
            widget_list = payload["widgetList"]
            return widget_list[0]["data"]["devices"][0]
        except (KeyError, IndexError, TypeError) as exception:
            raise SensusAnalyticsApiClientCommunicationError(
                "Daily data response did not contain a meter device",
            ) from exception

    async def _async_get_hourly_data(
        self,
        *,
        account_number: str,
        meter_number: str,
        target_date: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch hourly usage and weather data for a local date."""
        start_ts, end_ts = self._start_end_timestamps(target_date)
        try:
            async with self._session.get(
                self._url(f"water/usage/{account_number}/{meter_number}"),
                params={
                    "start": start_ts,
                    "end": end_ts,
                    "zoom": "day",
                    "page": "null",
                    "weather": "1",
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status in (401, 403):
                    _raise_authentication_error(
                        f"Hourly data request failed with status {response.status}",
                    )
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except SensusAnalyticsApiClientAuthenticationError:
            raise
        except (TimeoutError, aiohttp.ClientError, socket.gaierror) as exception:
            raise SensusAnalyticsApiClientCommunicationError(
                f"Hourly data request failed: {exception}",
            ) from exception

        return self._parse_hourly_data(payload)

    def _url(self, path: str) -> str:
        """Return an absolute Sensus endpoint URL."""
        return urljoin(self._base_url, path)

    @staticmethod
    def _parse_hourly_data(payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalize the Sensus hourly data response."""
        if not isinstance(payload, dict):
            raise SensusAnalyticsApiClientCommunicationError("Hourly data response was not an object")

        if not payload.get("operationSuccess", False):
            raise SensusAnalyticsApiClientCommunicationError(
                f"Hourly data response reported errors: {payload.get('errors', [])}",
            )

        usage_list = payload.get("data", {}).get("usage", [])
        if not usage_list:
            return []

        units = usage_list[0]
        if not isinstance(units, list) or len(units) < 3:
            raise SensusAnalyticsApiClientCommunicationError("Hourly data response did not include units")

        hourly_entries: list[dict[str, Any]] = []
        for entry in usage_list[1:]:
            if not isinstance(entry, list) or len(entry) < 4:
                continue
            timestamp, usage, rain, temp = entry[:4]
            hourly_entries.append(
                {
                    "timestamp": timestamp,
                    "usage": usage,
                    "rain": rain,
                    "temp": temp,
                    "usage_unit": units[0],
                    "rain_unit": units[1],
                    "temp_unit": units[2],
                },
            )

        return hourly_entries

    @staticmethod
    def _start_end_timestamps(target_date: datetime) -> tuple[int, int]:
        """Return local day start/end Unix timestamps in milliseconds."""
        local_tz = target_date.tzinfo or dt_util.DEFAULT_TIME_ZONE
        start_dt = datetime.combine(target_date.date(), time.min, tzinfo=local_tz)
        end_dt = datetime.combine(target_date.date(), time.max, tzinfo=local_tz)
        return int(start_dt.timestamp() * 1000), int(end_dt.timestamp() * 1000)
