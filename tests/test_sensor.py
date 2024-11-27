"""Test suite for the Sensus Analytics Integration sensors."""

from unittest.mock import patch

import pytest
import pytest_asyncio
from homeassistant.config_entries import ConfigEntry
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


@pytest.fixture
def config_entry():
    """Fixture for ConfigEntry."""
    return ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test Entry",
        data={},
        source="test",
        entry_id="test_entry_id",
        unique_id="test_unique_id",
    )


@pytest_asyncio.fixture
async def coordinator(hass: HomeAssistant, config_entry):
    """Fixture for the DataUpdateCoordinator."""
    test_data = {
        "usageUnit": "CF",
        "meterAddress1": "1 OAKMONT",
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
        coordinator = SensusAnalyticsDataUpdateCoordinator(hass, config_entry)
        await coordinator.async_config_entry_first_refresh()
        return coordinator


@pytest.mark.asyncio
async def test_daily_usage_sensor(hass: HomeAssistant, coordinator, config_entry):
    """Test the daily usage sensor."""
    sensor = SensusAnalyticsDailyUsageSensor(coordinator, config_entry)
    assert sensor.name == "Sensus Analytics Daily Usage"
    assert sensor.unique_id == f"{DOMAIN}_{config_entry.entry_id}_daily_usage"
    assert sensor.native_value == 18.0
    assert sensor.native_unit_of_measurement == "CF"
    assert sensor.icon == "mdi:water"


@pytest.mark.asyncio
async def test_usage_unit_sensor(hass: HomeAssistant, coordinator, config_entry):
    """Test the usage unit sensor."""
    sensor = SensusAnalyticsUsageUnitSensor(coordinator, config_entry)
    assert sensor.name == "Sensus Analytics Usage Unit"
    assert sensor.unique_id == f"{DOMAIN}_{config_entry.entry_id}_usage_unit"
    assert sensor.native_value == "CF"
    assert sensor.icon == "mdi:format-float"


@pytest.mark.asyncio
async def test_meter_address_sensor(hass: HomeAssistant, coordinator, config_entry):
    """Test the meter address sensor."""
    sensor = SensusAnalyticsMeterAddressSensor(coordinator, config_entry)
    assert sensor.name == "Sensus Analytics Meter Address"
    assert sensor.unique_id == f"{DOMAIN}_{config_entry.entry_id}_meter_address"
    assert sensor.native_value == "1 OAKMONT"
    assert sensor.icon == "mdi:map-marker"


@pytest.mark.asyncio
async def test_last_read_sensor(hass: HomeAssistant, coordinator, config_entry):
    """Test the last read sensor."""
    sensor = SensusAnalyticsLastReadSensor(coordinator, config_entry)
    assert sensor.name == "Sensus Analytics Last Read"
    assert sensor.unique_id == f"{DOMAIN}_{config_entry.entry_id}_last_read"
    expected_time = dt_util.utc_from_timestamp(1732607999.000).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    assert sensor.native_value == expected_time
    assert sensor.icon == "mdi:clock-time-nine"


@pytest.mark.asyncio
async def test_billing_sensor(hass: HomeAssistant, coordinator, config_entry):
    """Test the billing sensor."""
    sensor = SensusAnalyticsBillingSensor(coordinator, config_entry)
    assert sensor.name == "Sensus Analytics Billing Active"
    assert sensor.unique_id == f"{DOMAIN}_{config_entry.entry_id}_billing"
    assert sensor.native_value is True
    assert sensor.icon == "mdi:currency-usd"


@pytest.mark.asyncio
async def test_meter_longitude_sensor(hass: HomeAssistant, coordinator, config_entry):
    """Test the meter longitude sensor."""
    sensor = SensusAnalyticsMeterLongitudeSensor(coordinator, config_entry)
    assert sensor.name == "Sensus Analytics Meter Longitude"
    assert sensor.unique_id == f"{DOMAIN}_{config_entry.entry_id}_meter_longitude"
    assert sensor.native_value == -120.457214
    assert sensor.native_unit_of_measurement == "°"
    assert sensor.icon == "mdi:longitude"


@pytest.mark.asyncio
async def test_alert_count_sensor(hass: HomeAssistant, coordinator, config_entry):
    """Test the alert count sensor."""
    sensor = SensusAnalyticsAlertCountSensor(coordinator, config_entry)
    assert sensor.name == "Sensus Analytics Alert Count"
    assert sensor.unique_id == f"{DOMAIN}_{config_entry.entry_id}_alert_count"
    assert sensor.native_value == 0
    assert sensor.native_unit_of_measurement == "Alerts"
    assert sensor.icon == "mdi:alert"


@pytest.mark.asyncio
async def test_meter_id_sensor(hass: HomeAssistant, coordinator, config_entry):
    """Test the meter ID sensor."""
    sensor = SensusAnalyticsMeterIdSensor(coordinator, config_entry)
    assert sensor.name == "Sensus Analytics Meter ID"
    assert sensor.unique_id == f"{DOMAIN}_{config_entry.entry_id}_meter_id"
    assert sensor.native_value == "79071217"
    assert sensor.icon == "mdi:account"


@pytest.mark.asyncio
async def test_meter_latitude_sensor(hass: HomeAssistant, coordinator, config_entry):
    """Test the meter latitude sensor."""
    sensor = SensusAnalyticsMeterLatitudeSensor(coordinator, config_entry)
    assert sensor.name == "Sensus Analytics Meter Latitude"
    assert sensor.unique_id == f"{DOMAIN}_{config_entry.entry_id}_meter_latitude"
    assert sensor.native_value == 30.637222
    assert sensor.native_unit_of_measurement == "°"
    assert sensor.icon == "mdi:latitude"


@pytest.mark.asyncio
async def test_latest_read_usage_sensor(hass: HomeAssistant, coordinator, config_entry):
    """Test the latest read usage sensor."""
    sensor = SensusAnalyticsLatestReadUsageSensor(coordinator, config_entry)
    assert sensor.name == "Sensus Analytics Latest Read Usage"
    assert sensor.unique_id == f"{DOMAIN}_{config_entry.entry_id}_latest_read_usage"
    assert sensor.native_value == "94139.00"
    assert sensor.native_unit_of_measurement == "CF"
    assert sensor.icon == "mdi:water"


@pytest.mark.asyncio
async def test_latest_read_time_sensor(hass: HomeAssistant, coordinator, config_entry):
    """Test the latest read time sensor."""
    sensor = SensusAnalyticsLatestReadTimeSensor(coordinator, config_entry)
    assert sensor.name == "Sensus Analytics Latest Read Time"
    assert sensor.unique_id == f"{DOMAIN}_{config_entry.entry_id}_latest_read_time"
    expected_time = dt_util.utc_from_timestamp(1732604400.000).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    assert sensor.native_value == expected_time
    assert sensor.icon == "mdi:clock-time-nine"


@pytest.mark.asyncio
async def test_billing_usage_sensor(hass: HomeAssistant, coordinator, config_entry):
    """Test the billing usage sensor."""
    sensor = SensusAnalyticsBillingUsageSensor(coordinator, config_entry)
    assert sensor.name == "Sensus Analytics Billing Usage"
    assert sensor.unique_id == f"{DOMAIN}_{config_entry.entry_id}_billing_usage"
    assert sensor.native_value == 2202.0
    assert sensor.native_unit_of_measurement == "CF"
    assert sensor.icon == "mdi:currency-usd"
