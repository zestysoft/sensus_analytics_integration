"""Tests for the Sensus Analytics API client."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from zoneinfo import ZoneInfo

import pytest

from custom_components.sensus_analytics.api import SensusAnalyticsApiClient, SensusAnalyticsApiClientAuthenticationError


class FakeResponse:
    """Minimal async response context manager."""

    def __init__(self, status: int, payload: dict | None = None) -> None:
        """Initialize the fake response."""
        self.status = status
        self._payload = payload or {}

    async def __aenter__(self) -> Self:
        """Enter the response context."""
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Exit the response context."""

    def raise_for_status(self) -> None:
        """Raise for unexpected HTTP status codes."""
        if self.status >= 400:
            msg = f"HTTP {self.status}"
            raise RuntimeError(msg)

    async def json(self, content_type: str | None = None) -> dict:
        """Return the response payload."""
        return self._payload


class FakeSession:
    """Minimal aiohttp-like session for client tests."""

    def __init__(self, *, login_status: int = 302) -> None:
        """Initialize the fake session."""
        self.login_status = login_status
        self.posts: list[dict] = []
        self.gets: list[dict] = []

    def post(self, url: str, **kwargs) -> FakeResponse:
        """Return fake login or daily response."""
        self.posts.append({"url": url, **kwargs})
        if url.endswith("j_spring_security_check"):
            return FakeResponse(self.login_status)
        return FakeResponse(
            200,
            {
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
            },
        )

    def get(self, url: str, **kwargs) -> FakeResponse:
        """Return fake hourly response."""
        self.gets.append({"url": url, **kwargs})
        return FakeResponse(
            200,
            {
                "operationSuccess": True,
                "data": {
                    "usage": [
                        ["CF", "INCHES", "FAHRENHEIT"],
                        [1714564800000, 1.25, 0.0, 70.0],
                    ],
                },
            },
        )


@pytest.mark.asyncio
async def test_async_get_data_fetches_daily_and_hourly_data() -> None:
    """Client authenticates, fetches daily data, and normalizes hourly data."""
    session = FakeSession()
    client = SensusAnalyticsApiClient(
        base_url="https://example.sensus-analytics.com",
        username="user",
        password="pass",
        session=session,
    )

    data = await client.async_get_data(
        account_number="123",
        meter_number="456",
        target_date=datetime(2024, 5, 1, tzinfo=ZoneInfo("America/Los_Angeles")),
    )

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


@pytest.mark.asyncio
async def test_async_authenticate_raises_for_failed_login() -> None:
    """Client raises a domain auth error for non-redirect login responses."""
    client = SensusAnalyticsApiClient(
        base_url="https://example.sensus-analytics.com/",
        username="user",
        password="bad",
        session=FakeSession(login_status=200),
    )

    with pytest.raises(SensusAnalyticsApiClientAuthenticationError):
        await client.async_authenticate()
