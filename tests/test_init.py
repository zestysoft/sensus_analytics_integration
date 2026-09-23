"""Tests for Sensus Analytics setup, config flows, and entry reloads."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.sensus_analytics.api import (
    SensusAnalyticsApiClient,
    SensusAnalyticsApiClientAuthenticationError,
    SensusAnalyticsApiClientCommunicationError,
)
from custom_components.sensus_analytics.const import (
    CONF_ACCOUNT_NUMBER,
    CONF_BASE_URL,
    CONF_METER_NUMBER,
    CONF_SERVICE_FEE,
    CONF_TIER1_PRICE,
    CONF_UNIT_TYPE,
    CONF_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    UNIT_CCF,
    UNIT_GALLONS,
)
from homeassistant import config_entries
from homeassistant.components.recorder import Recorder
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

CONNECTION_DATA = {
    CONF_BASE_URL: "https://city.sensus-analytics.com/",
    CONF_USERNAME: "user",
    CONF_PASSWORD: "pass",
    CONF_ACCOUNT_NUMBER: "123",
    CONF_METER_NUMBER: "456",
}
ENTRY_DATA = {
    **CONNECTION_DATA,
    CONF_UNIT_TYPE: UNIT_CCF,
    CONF_TIER1_PRICE: 4.0,
    CONF_SERVICE_FEE: 15.0,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock: Recorder, enable_custom_integrations: None) -> None:
    """Allow Home Assistant to load the integration under test (the recorder is a dependency)."""


def _daily_data(hourly: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return client data as async_get_data would."""
    data: dict[str, Any] = {"dailyUsage": 100, "billingUsage": 500, "usageUnit": "CF"}
    if hourly is not None:
        data["hourly_usage_data"] = hourly
    return data


@pytest.fixture
def mock_get_data() -> Generator[AsyncMock]:
    """Patch the Sensus client's data fetch."""
    with patch.object(
        SensusAnalyticsApiClient,
        "async_get_data",
        AsyncMock(side_effect=lambda **_: _daily_data()),
    ) as mock:
        yield mock


def _entry(**kwargs: Any) -> MockConfigEntry:
    """Return a Sensus config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Sensus Analytics",
        data=ENTRY_DATA,
        unique_id="123_456",
        **kwargs,
    )


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add and set up a config entry."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


async def test_each_entry_gets_its_own_session(hass: HomeAssistant, mock_get_data: AsyncMock) -> None:
    """Entries don't share the login cookie jar with each other or Home Assistant, and unload detaches it."""
    first = _entry()
    second = MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, CONF_METER_NUMBER: "789"},
        unique_id="123_789",
    )
    await _setup(hass, first)
    await _setup(hass, second)

    first_session = first.runtime_data.client._session  # noqa: SLF001
    second_session = second.runtime_data.client._session  # noqa: SLF001
    assert first_session is not async_get_clientsession(hass)
    assert first_session is not second_session
    assert first_session.cookie_jar is not second_session.cookie_jar

    assert await hass.config_entries.async_unload(first.entry_id)
    assert first_session.closed
    assert not second_session.closed


async def test_setup_uses_no_update_listener(hass: HomeAssistant, mock_get_data: AsyncMock) -> None:
    """Coordinator updates always reach entities and there is no reload-on-update listener."""
    entry = _entry()
    await _setup(hass, entry)

    assert entry.runtime_data.coordinator.always_update is True
    assert entry.update_listeners == []


async def test_last_hour_sensors_follow_the_clock(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """The "last hour" sensors move to the next hour's data at the top of the hour without a new poll."""
    local_tz = dt_util.get_time_zone(hass.config.time_zone)
    freezer.move_to(datetime(2024, 5, 2, 10, 30, tzinfo=local_tz))
    hourly = [
        {
            "timestamp": int(datetime(2024, 5, 1, hour, tzinfo=local_tz).timestamp() * 1000),
            "usage": 1.0,
            "rain": rain,
            "temp": 70.0,
            "usage_unit": UNIT_CCF,
        }
        for hour, rain in ((10, 0.1), (11, 0.25))
    ]
    # A long poll interval proves the hourly refresh doesn't depend on polling
    entry = _entry(options={CONF_UPDATE_INTERVAL_MINUTES: 1440})

    with patch.object(
        SensusAnalyticsApiClient,
        "async_get_data",
        AsyncMock(side_effect=lambda **_: _daily_data(hourly)),
    ) as mock_get_data:
        await _setup(hass, entry)
        entity_id = er.async_get(hass).async_get_entity_id(
            "sensor",
            DOMAIN,
            f"{DOMAIN}_{entry.entry_id}_last_hour_rainfall",
        )
        assert entity_id is not None
        assert hass.states.get(entity_id).state == "0.1"

        freezer.move_to(datetime(2024, 5, 2, 11, 0, 0, tzinfo=local_tz))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

        assert hass.states.get(entity_id).state == "0.25"
        assert mock_get_data.call_count == 1


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (SensusAnalyticsApiClientAuthenticationError("bad password"), "auth"),
        (SensusAnalyticsApiClientCommunicationError("503"), "connection"),
    ],
)
async def test_user_flow_maps_errors(hass: HomeAssistant, exception: Exception, error: str) -> None:
    """Bad credentials show "auth" and outages show "connection"."""
    with patch.object(SensusAnalyticsApiClient, "async_authenticate", AsyncMock(side_effect=exception)):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=ENTRY_DATA,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_reconfigure_updates_connection_only_and_reloads_once(
    hass: HomeAssistant,
    mock_get_data: AsyncMock,
) -> None:
    """Reconfigure edits connection settings, keeps display/pricing settings, and reloads once."""
    entry = _entry(options={CONF_UNIT_TYPE: UNIT_GALLONS, CONF_TIER1_PRICE: 0.01, CONF_SERVICE_FEE: 10.0})
    await _setup(hass, entry)
    assert mock_get_data.call_count == 1

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert {str(key) for key in result["data_schema"].schema} == set(CONNECTION_DATA)

    with patch.object(SensusAnalyticsApiClient, "async_authenticate", AsyncMock()):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {**CONNECTION_DATA, CONF_PASSWORD: "new-pass", CONF_METER_NUMBER: "789"},
        )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.unique_id == "123_789"
    assert entry.data[CONF_PASSWORD] == "new-pass"
    assert entry.data[CONF_UNIT_TYPE] == UNIT_CCF
    assert entry.options[CONF_UNIT_TYPE] == UNIT_GALLONS
    assert mock_get_data.call_count == 2


async def test_reconfigure_rejects_meter_of_another_entry(hass: HomeAssistant, mock_get_data: AsyncMock) -> None:
    """Reconfigure can't point an entry at an account and meter another entry already uses."""
    entry = _entry()
    await _setup(hass, entry)
    MockConfigEntry(domain=DOMAIN, data={**ENTRY_DATA, CONF_METER_NUMBER: "789"}, unique_id="123_789").add_to_hass(
        hass,
    )

    result = await entry.start_reconfigure_flow(hass)
    with patch.object(SensusAnalyticsApiClient, "async_authenticate", AsyncMock()):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {**CONNECTION_DATA, CONF_METER_NUMBER: "789"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.unique_id == "123_456"


async def test_reauth_reloads_once(hass: HomeAssistant, mock_get_data: AsyncMock) -> None:
    """Reauth stores the new password and reloads the entry once."""
    entry = _entry()
    await _setup(hass, entry)

    result = await entry.start_reauth_flow(hass)
    with patch.object(SensusAnalyticsApiClient, "async_authenticate", AsyncMock()):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "user", CONF_PASSWORD: "new-pass"},
        )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "new-pass"
    assert mock_get_data.call_count == 2


async def test_options_change_reloads_once(hass: HomeAssistant, mock_get_data: AsyncMock) -> None:
    """Saving new options reloads the entry once."""
    entry = _entry()
    await _setup(hass, entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_UNIT_TYPE: UNIT_GALLONS,
            CONF_TIER1_PRICE: 0.01,
            CONF_SERVICE_FEE: 15.0,
            CONF_UPDATE_INTERVAL_MINUTES: 5,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_UNIT_TYPE] == UNIT_GALLONS
    assert mock_get_data.call_count == 2
