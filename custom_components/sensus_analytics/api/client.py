"""Async API client for Sensus Analytics."""

from __future__ import annotations

from datetime import datetime, time
import socket
from typing import Any, NoReturn
from urllib.parse import urljoin, urlsplit

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
        """Authenticate the client session against Sensus Analytics."""
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
                status = response.status
                location = response.headers.get("Location", "")
        except (TimeoutError, aiohttp.ClientError, socket.gaierror) as exception:
            raise SensusAnalyticsApiClientCommunicationError(
                f"Authentication request failed: {exception}",
            ) from exception

        # Spring Security redirects on success and either redirects back to the login page with an
        # error marker (for example "?error" or "login.html#/failed") or re-renders the login form (200)
        # when the credentials are rejected
        if status == 302:
            redirect = urlsplit(location)
            markers = f"{redirect.query}#{redirect.fragment}".lower()
            if "error" in markers or "fail" in markers:
                _raise_authentication_error("Sensus Analytics rejected the username or password")
            return
        if status in (200, 401):
            _raise_authentication_error(f"Authentication failed with status {status}")
        # Anything else (5xx, 429, a 403 from a firewall, ...) is a service problem, not a credential problem
        raise SensusAnalyticsApiClientCommunicationError(
            f"Authentication request returned unexpected status {status}",
        )

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
        except SensusAnalyticsApiClientError as exception:
            # Hourly data only feeds the "last hour" sensors, so never let it fail the whole update
            LOGGER.warning("Failed to fetch Sensus hourly data: %s", exception)
        else:
            daily_data["hourly_usage_data"] = hourly_data

        return daily_data

    async def async_get_hourly_data(
        self,
        *,
        account_number: str,
        meter_number: str,
        target_date: datetime,
        authenticate: bool = True,
    ) -> list[dict[str, Any]]:
        """Fetch one local day's hourly usage and weather data.

        The login is refreshed first unless the caller has just authenticated (for example
        when fetching several days in a row).
        """
        if authenticate:
            await self.async_authenticate()
        return await self._async_get_hourly_data(
            account_number=account_number,
            meter_number=meter_number,
            target_date=target_date,
        )

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
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, socket.gaierror) as exception:
            raise SensusAnalyticsApiClientCommunicationError(
                f"Daily data request failed: {exception}",
            ) from exception
        except ValueError as exception:
            # An HTML maintenance or login page instead of JSON
            raise SensusAnalyticsApiClientCommunicationError(
                "Daily data response was not valid JSON",
            ) from exception

        try:
            widget_data = payload["widgetList"][0]["data"]
        except (KeyError, IndexError, TypeError) as exception:
            raise SensusAnalyticsApiClientCommunicationError(
                "Daily data response did not contain meter data",
            ) from exception

        # Sensus answers with "nodata" and an empty device list while its backend is having trouble
        devices = widget_data.get("devices") if isinstance(widget_data, dict) else None
        if not devices:
            raise SensusAnalyticsApiClientCommunicationError(
                "Sensus Analytics returned no meter data; the service may be temporarily unavailable",
            )
        return devices[0]

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
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, socket.gaierror) as exception:
            raise SensusAnalyticsApiClientCommunicationError(
                f"Hourly data request failed: {exception}",
            ) from exception
        except ValueError as exception:
            raise SensusAnalyticsApiClientCommunicationError(
                "Hourly data response was not valid JSON",
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

        data = payload.get("data")
        usage_list = data.get("usage") if isinstance(data, dict) else None
        if not usage_list:
            return []
        if not isinstance(usage_list, list):
            raise SensusAnalyticsApiClientCommunicationError("Hourly data response did not include a usage list")

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
