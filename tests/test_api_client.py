"""Tests for the Sensus Analytics API client."""

from __future__ import annotations

from datetime import datetime
import json
from typing import Self
from zoneinfo import ZoneInfo

import aiohttp
from multidict import CIMultiDict, CIMultiDictProxy
import pytest
from yarl import URL

from custom_components.sensus_analytics.api import (
    SensusAnalyticsApiClient,
    SensusAnalyticsApiClientAuthenticationError,
    SensusAnalyticsApiClientCommunicationError,
)

BASE_URL = "https://example.sensus-analytics.com"
TARGET_DATE = datetime(2024, 5, 1, tzinfo=ZoneInfo("America/Los_Angeles"))
MAINTENANCE_PAGE = "<html><body>Down for maintenance</body></html>"

DAILY_PAYLOAD = {
    "widgetList": [
        {
            "data": {
                "devices": [
                    {
                        "dailyUsage": 10,
                        "usageUnit": "CF",
                        "billingUsage": 100,
                    },
                ],
            },
        },
    ],
}

HOURLY_PAYLOAD = {
    "operationSuccess": True,
    "data": {
        "usage": [
            ["CF", "INCHES", "FAHRENHEIT"],
            [1714564800000, 1.25, 0.0, 70.0],
        ],
    },
}


class FakeResponse:
    """Minimal aiohttp-like response context manager."""

    def __init__(
        self,
        status: int,
        payload: dict | None = None,
        *,
        body: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize the fake response with a JSON payload or a raw body."""
        self.status = status
        self.headers = CIMultiDictProxy(CIMultiDict(headers or {}))
        self._body = json.dumps(payload or {}) if body is None else body

    async def __aenter__(self) -> Self:
        """Enter the response context."""
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Exit the response context."""

    def raise_for_status(self) -> None:
        """Raise like aiohttp does for error status codes."""
        if self.status >= 400:
            url = URL(BASE_URL)
            raise aiohttp.ClientResponseError(
                aiohttp.RequestInfo(url, "GET", CIMultiDictProxy(CIMultiDict()), url),
                (),
                status=self.status,
                message=f"HTTP {self.status}",
            )

    async def json(self, content_type: str | None = None) -> dict:
        """Decode the body like aiohttp does, raising JSONDecodeError on non-JSON."""
        return json.loads(self._body)


class FakeSession:
    """Minimal aiohttp-like session for client tests."""

    def __init__(
        self,
        *,
        login_status: int = 302,
        login_location: str = f"{BASE_URL}/water/",
        daily_payload: dict | None = None,
        daily_response: FakeResponse | None = None,
        hourly_response: FakeResponse | None = None,
    ) -> None:
        """Initialize the fake session."""
        self.login_status = login_status
        self.login_location = login_location
        self.daily_response = daily_response or FakeResponse(200, daily_payload or DAILY_PAYLOAD)
        self.hourly_response = hourly_response or FakeResponse(200, HOURLY_PAYLOAD)
        self.posts: list[dict] = []
        self.gets: list[dict] = []

    def post(self, url: str, **kwargs) -> FakeResponse:
        """Return fake login or daily response."""
        self.posts.append({"url": url, **kwargs})
        if url.endswith("j_spring_security_check"):
            headers = {"Location": self.login_location} if self.login_status == 302 else {}
            return FakeResponse(self.login_status, body="", headers=headers)
        return self.daily_response

    def get(self, url: str, **kwargs) -> FakeResponse:
        """Return fake hourly response."""
        self.gets.append({"url": url, **kwargs})
        return self.hourly_response


def _client(session: FakeSession) -> SensusAnalyticsApiClient:
    """Return a client wired to a fake session."""
    return SensusAnalyticsApiClient(
        base_url=BASE_URL,
        username="user",
        password="pass",
        session=session,
    )


async def _get_data(client: SensusAnalyticsApiClient) -> dict:
    """Fetch data for the test meter."""
    return await client.async_get_data(account_number="123", meter_number="456", target_date=TARGET_DATE)


@pytest.mark.asyncio
async def test_async_get_data_fetches_daily_and_hourly_data() -> None:
    """Client authenticates, fetches daily data, and normalizes hourly data."""
    session = FakeSession()

    data = await _get_data(_client(session))

    assert data["dailyUsage"] == 10
    assert data["usageUnit"] == "CF"
    assert data["hourly_usage_data"] == [
        {
            "timestamp": 1714564800000,
            "usage": 1.25,
            "rain": 0.0,
            "temp": 70.0,
            "usage_unit": "CF",
            "rain_unit": "INCHES",
            "temp_unit": "FAHRENHEIT",
        },
    ]
    assert session.posts[0]["url"] == "https://example.sensus-analytics.com/j_spring_security_check"
    assert session.gets[0]["params"]["zoom"] == "day"


@pytest.mark.parametrize("status", [200, 401])
@pytest.mark.asyncio
async def test_async_authenticate_raises_for_rejected_credentials(status: int) -> None:
    """A re-rendered login form (200) or a 401 means the credentials were rejected."""
    client = _client(FakeSession(login_status=status))

    with pytest.raises(SensusAnalyticsApiClientAuthenticationError):
        await client.async_authenticate()


@pytest.mark.parametrize(
    "location",
    [
        f"{BASE_URL}/login?error",
        f"{BASE_URL}/login.jsp?login_error=1",
        f"{BASE_URL}/login.html#/failed",
    ],
)
@pytest.mark.asyncio
async def test_async_authenticate_raises_for_error_redirect(location: str) -> None:
    """Spring Security's redirect back to the login page with an error is a credential rejection."""
    client = _client(FakeSession(login_status=302, login_location=location))

    with pytest.raises(SensusAnalyticsApiClientAuthenticationError):
        await client.async_authenticate()


@pytest.mark.parametrize("status", [500, 502, 503, 429, 404, 403])
@pytest.mark.asyncio
async def test_async_authenticate_server_errors_are_communication_errors(status: int) -> None:
    """Server-side login failures must not be reported as bad credentials (which would force reauth)."""
    client = _client(FakeSession(login_status=status))

    with pytest.raises(SensusAnalyticsApiClientCommunicationError) as exc_info:
        await client.async_authenticate()
    assert not isinstance(exc_info.value, SensusAnalyticsApiClientAuthenticationError)


@pytest.mark.asyncio
async def test_async_get_data_raises_communication_error_for_nodata_response() -> None:
    """A "nodata" response with no devices is a clean communication error, not an IndexError."""
    nodata_payload = {
        "operationSuccess": True,
        "widgetList": [
            {
                "id": "meters",
                "size": 0,
                "data": {"devices": [], "nodata": True, "accountNumber": "123", "error": ["error"]},
                "commodity": "water",
            },
        ],
        "errors": [],
    }
    client = _client(FakeSession(daily_payload=nodata_payload))

    with pytest.raises(SensusAnalyticsApiClientCommunicationError, match="no meter data"):
        await _get_data(client)


@pytest.mark.asyncio
async def test_async_get_data_raises_communication_error_for_html_daily_response() -> None:
    """An HTML page instead of the daily JSON is a communication error, not an unhandled decode error."""
    client = _client(FakeSession(daily_response=FakeResponse(200, body=MAINTENANCE_PAGE)))

    with pytest.raises(SensusAnalyticsApiClientCommunicationError, match="not valid JSON"):
        await _get_data(client)


@pytest.mark.parametrize("status", [401, 403, 503])
@pytest.mark.asyncio
async def test_async_get_data_daily_http_errors_are_communication_errors(status: int) -> None:
    """Daily endpoint errors after a successful login are retried, not treated as bad credentials."""
    client = _client(FakeSession(daily_response=FakeResponse(status, body="")))

    with pytest.raises(SensusAnalyticsApiClientCommunicationError) as exc_info:
        await _get_data(client)
    assert not isinstance(exc_info.value, SensusAnalyticsApiClientAuthenticationError)


@pytest.mark.parametrize(
    "hourly_response",
    [
        FakeResponse(200, body=MAINTENANCE_PAGE),
        FakeResponse(403, body=""),
        FakeResponse(500, body=""),
        FakeResponse(200, {"operationSuccess": False, "errors": ["boom"]}),
        FakeResponse(200, {"operationSuccess": True, "data": {"usage": "unexpected"}}),
    ],
    ids=["html", "forbidden", "server_error", "operation_failed", "bad_shape"],
)
@pytest.mark.asyncio
async def test_async_get_data_returns_daily_data_when_hourly_fails(hourly_response: FakeResponse) -> None:
    """Hourly data is best effort: any hourly failure still returns the daily data."""
    client = _client(FakeSession(hourly_response=hourly_response))

    data = await _get_data(client)

    assert data["dailyUsage"] == 10
    assert "hourly_usage_data" not in data


@pytest.mark.asyncio
async def test_async_get_data_handles_null_hourly_data() -> None:
    """A null hourly "data" object yields no hourly entries instead of an AttributeError."""
    client = _client(FakeSession(hourly_response=FakeResponse(200, {"operationSuccess": True, "data": None})))

    data = await _get_data(client)

    assert data["dailyUsage"] == 10
    assert data.get("hourly_usage_data", []) == []


@pytest.mark.parametrize(("authenticate", "logins"), [(True, 1), (False, 0)])
@pytest.mark.asyncio
async def test_async_get_hourly_data_fetches_one_day(authenticate: bool, logins: int) -> None:
    """The public hourly fetch logs in unless told not to and requests the whole local day."""
    session = FakeSession()

    data = await _client(session).async_get_hourly_data(
        account_number="123",
        meter_number="456",
        target_date=TARGET_DATE,
        authenticate=authenticate,
    )

    assert [entry["usage"] for entry in data] == [1.25]
    assert len(session.posts) == logins
    assert session.gets[0]["url"] == "https://example.sensus-analytics.com/water/usage/123/456"
    start = datetime(2024, 5, 1, tzinfo=ZoneInfo("America/Los_Angeles"))
    assert session.gets[0]["params"]["start"] == int(start.timestamp() * 1000)
