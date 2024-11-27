"""Test suite for the Sensus Analytics Integration sensors."""

# pylint: disable=redefined-outer-name

from unittest.mock import patch

import pytest
import pytest_asyncio
from homeassistant.config_entries import (SOURCE_USER, ConfigEntry,
                                          ConfigEntryState)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.sensus_analytics.const import DOMAIN
from custom_components.sensus_analytics.coordinator import \
    SensusAnalyticsDataUpdateCoordinator
from custom_components.sensus_analytics.sensor import (
    SensusAnalyticsAlertCountSensor, SensusAnalyticsBillingSensor,
    SensusAnalyticsBillingUsageSensor, SensusAnalyticsDailyUsageSensor,
    SensusAnalyticsLastReadSensor, SensusAnalyticsLatestReadTimeSensor,
    SensusAnalyticsLatestReadUsageSensor, SensusAnalyticsMeterAddressSensor,
    SensusAnalyticsMeterIdSensor, SensusAnalyticsMeterLatitudeSensor,
    SensusAnalyticsMeterLongitudeSensor, SensusAnalyticsUsageUnitSensor)


@pytest.fixture(name="config_entry_fixture")
def config_entry_fixture():
    """Fixture for ConfigEntry."""
    return ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Entry",
        data={},
        source=SOURCE_USER,
        options={},
        entry_id="test_entry_id",
        unique_id="test_unique_id",
        disabled_by=None,
        state=ConfigEntryState.NOT_LOADED,
        discovery_keys=[],
    )


@pytest_asyncio.fixture(name="coordinator_fixture")
async def coordinator_fixture(hass: HomeAssistant, config_entry_fixture):
    """Fixture for the DataUpdateCoordinator."""
    test_data = {
        "usageUnit": "CF",
        "meterAddress1": "1 STREETNAME",
        "lastRead": 1732607999000,
        "billing": True,
        "dailyUsage": 18.0,
        "meterLong": -120.457214,
        "alertCount": 0,
        "meterId": "79071217",
        "meterLat": 30.637222,
        "latestReadUsage": "94139.00",
        "latestReadTime": 1732604400000,
        "billingUsage": 2202.0,
    }

    with patch.object(
        SensusAnalyticsDataUpdateCoordinator,
        "_async_update_data",
        return_value=test_data,
    ):
        coordinator = SensusAnalyticsDataUpdateCoordinator(hass, config_entry_fixture)
        await coordinator.async_config_entry_first_refresh()
        return coordinator


@pytest.mark.asyncio
async def test_daily_usage_sensor(coordinator_fixture, config_entry_fixture):
    """Test the daily usage sensor."""
    sensor = SensusAnalyticsDailyUsageSensor(coordinator_fixture, config_entry_fixture)
    assert sensor.name == "Sensus Analytics Daily Usage"  # nosec B101
    assert (
        sensor.unique_id == f"{DOMAIN}_{config_entry_fixture.entry_id}_daily_usage"
    )  # nosec B101
    assert sensor.native_value == 18.0  # nosec B101
    assert sensor.native_unit_of_measurement == "CF"  # nosec B101
    assert sensor.icon == "mdi:water"  # nosec B101


@pytest.mark.asyncio
async def test_usage_unit_sensor(coordinator_fixture, config_entry_fixture):
    """Test the usage unit sensor."""
    sensor = SensusAnalyticsUsageUnitSensor(coordinator_fixture, config_entry_fixture)
    assert sensor.name == "Sensus Analytics Usage Unit"  # nosec B101
    assert (
        sensor.unique_id == f"{DOMAIN}_{config_entry_fixture.entry_id}_usage_unit"
    )  # nosec B101
    assert sensor.native_value == "CF"  # nosec B101
    assert sensor.icon == "mdi:format-float"  # nosec B101


@pytest.mark.asyncio
async def test_meter_address_sensor(coordinator_fixture, config_entry_fixture):
    """Test the meter address sensor."""
    sensor = SensusAnalyticsMeterAddressSensor(
        coordinator_fixture, config_entry_fixture
    )
    assert sensor.name == "Sensus Analytics Meter Address"  # nosec B101
    assert (
        sensor.unique_id == f"{DOMAIN}_{config_entry_fixture.entry_id}_meter_address"
    )  # nosec B101
    assert sensor.native_value == "1 STREETNAME"  # nosec B101
    assert sensor.icon == "mdi:map-marker"  # nosec B101


@pytest.mark.asyncio
async def test_last_read_sensor(coordinator_fixture, config_entry_fixture):
    """Test the last read sensor."""
    sensor = SensusAnalyticsLastReadSensor(coordinator_fixture, config_entry_fixture)
    assert sensor.name == "Sensus Analytics Last Read"  # nosec B101
    assert (
        sensor.unique_id == f"{DOMAIN}_{config_entry_fixture.entry_id}_last_read"
    )  # nosec B101
    expected_time = dt_util.utc_from_timestamp(1732607999.000).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    assert sensor.native_value == expected_time  # nosec B101
    assert sensor.icon == "mdi:clock-time-nine"  # nosec B101


@pytest.mark.asyncio
async def test_billing_sensor(coordinator_fixture, config_entry_fixture):
    """Test the billing sensor."""
    sensor = SensusAnalyticsBillingSensor(coordinator_fixture, config_entry_fixture)
    assert sensor.name == "Sensus Analytics Billing Active"  # nosec B101
    assert (
        sensor.unique_id == f"{DOMAIN}_{config_entry_fixture.entry_id}_billing"
    )  # nosec B101
    assert sensor.native_value is True  # nosec B101
    assert sensor.icon == "mdi:currency-usd"  # nosec B101


@pytest.mark.asyncio
async def test_meter_longitude_sensor(coordinator_fixture, config_entry_fixture):
    """Test the meter longitude sensor."""
    sensor = SensusAnalyticsMeterLongitudeSensor(
        coordinator_fixture, config_entry_fixture
    )
    assert sensor.name == "Sensus Analytics Meter Longitude"  # nosec B101
    assert (
        sensor.unique_id
        == f"{DOMAIN}_{config_entry_fixture.entry_id}_meter_longitude"  # nosec B101
    )
    assert sensor.native_value == -120.457214  # nosec B101
    assert sensor.native_unit_of_measurement == "°"  # nosec B101
    assert sensor.icon == "mdi:longitude"  # nosec B101


@pytest.mark.asyncio
async def test_alert_count_sensor(coordinator_fixture, config_entry_fixture):
    """Test the alert count sensor."""
    sensor = SensusAnalyticsAlertCountSensor(coordinator_fixture, config_entry_fixture)
    assert sensor.name == "Sensus Analytics Alert Count"  # nosec B101
    assert (
        sensor.unique_id == f"{DOMAIN}_{config_entry_fixture.entry_id}_alert_count"
    )  # nosec B101
    assert sensor.native_value == 0  # nosec B101
    assert sensor.native_unit_of_measurement == "Alerts"  # nosec B101
    assert sensor.icon == "mdi:alert"  # nosec B101


@pytest.mark.asyncio
async def test_meter_id_sensor(coordinator_fixture, config_entry_fixture):
    """Test the meter ID sensor."""
    sensor = SensusAnalyticsMeterIdSensor(coordinator_fixture, config_entry_fixture)
    assert sensor.name == "Sensus Analytics Meter ID"  # nosec B101
    assert (
        sensor.unique_id == f"{DOMAIN}_{config_entry_fixture.entry_id}_meter_id"
    )  # nosec B101
    assert sensor.native_value == "79071217"  # nosec B101
    assert sensor.icon == "mdi:account"  # nosec B101


@pytest.mark.asyncio
async def test_meter_latitude_sensor(coordinator_fixture, config_entry_fixture):
    """Test the meter latitude sensor."""
    sensor = SensusAnalyticsMeterLatitudeSensor(
        coordinator_fixture, config_entry_fixture
    )
    assert sensor.name == "Sensus Analytics Meter Latitude"  # nosec B101
    assert (
        sensor.unique_id
        == f"{DOMAIN}_{config_entry_fixture.entry_id}_meter_latitude"  # nosec B101
    )
    assert sensor.native_value == 30.637222  # nosec B101
    assert sensor.native_unit_of_measurement == "°"  # nosec B101
    assert sensor.icon == "mdi:latitude"  # nosec B101


@pytest.mark.asyncio
async def test_latest_read_usage_sensor(coordinator_fixture, config_entry_fixture):
    """Test the latest read usage sensor."""
    sensor = SensusAnalyticsLatestReadUsageSensor(
        coordinator_fixture, config_entry_fixture
    )
    assert sensor.name == "Sensus Analytics Latest Read Usage"  # nosec B101
    assert (
        sensor.unique_id
        == f"{DOMAIN}_{config_entry_fixture.entry_id}_latest_read_usage"  # nosec B101
    )
    assert sensor.native_value == "94139.00"  # nosec B101
    assert sensor.native_unit_of_measurement == "CF"  # nosec B101
    assert sensor.icon == "mdi:water"  # nosec B101


@pytest.mark.asyncio
async def test_latest_read_time_sensor(coordinator_fixture, config_entry_fixture):
    """Test the latest read time sensor."""
    sensor = SensusAnalyticsLatestReadTimeSensor(
        coordinator_fixture, config_entry_fixture
    )
    assert sensor.name == "Sensus Analytics Latest Read Time"  # nosec B101
    assert (
        sensor.unique_id
        == f"{DOMAIN}_{config_entry_fixture.entry_id}_latest_read_time"  # nosec B101
    )
    expected_time = dt_util.utc_from_timestamp(1732604400.000).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    assert sensor.native_value == expected_time  # nosec B101
    assert sensor.icon == "mdi:clock-time-nine"  # nosec B101


@pytest.mark.asyncio
async def test_billing_usage_sensor(coordinator_fixture, config_entry_fixture):
    """Test the billing usage sensor."""
    sensor = SensusAnalyticsBillingUsageSensor(
        coordinator_fixture, config_entry_fixture
    )
    assert sensor.name == "Sensus Analytics Billing Usage"  # nosec B101
    assert (
        sensor.unique_id == f"{DOMAIN}_{config_entry_fixture.entry_id}_billing_usage"
    )  # nosec B101
    assert sensor.native_value == 2202.0  # nosec B101
    assert sensor.native_unit_of_measurement == "CF"  # nosec B101
    assert sensor.icon == "mdi:currency-usd"  # nosec B101
