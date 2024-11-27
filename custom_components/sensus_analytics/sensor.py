"""Sensor platform for the Sensus Analytics Integration."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import SensusAnalyticsDataUpdateCoordinator

CF_TO_GALLON = 7.48052


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the Sensus Analytics sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SensusAnalyticsDailyUsageSensor(coordinator, entry),
            SensusAnalyticsUsageUnitSensor(coordinator, entry),
            SensusAnalyticsMeterAddressSensor(coordinator, entry),
            SensusAnalyticsLastReadSensor(coordinator, entry),
            SensusAnalyticsBillingSensor(coordinator, entry),
            SensusAnalyticsMeterLongitudeSensor(coordinator, entry),
            SensusAnalyticsAlertCountSensor(coordinator, entry),
            SensusAnalyticsMeterIdSensor(coordinator, entry),
            SensusAnalyticsMeterLatitudeSensor(coordinator, entry),
            SensusAnalyticsLatestReadUsageSensor(coordinator, entry),
            SensusAnalyticsLatestReadTimeSensor(coordinator, entry),
            SensusAnalyticsBillingUsageSensor(coordinator, entry),
        ],
        True,
    )


class SensusAnalyticsSensorBase(SensorEntity):
    """Base class for Sensus Analytics Sensors."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._unique_id = f"{DOMAIN}_{entry.entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Unknown",
            model="Water Meter",
        )

    @property
    def available(self):
        """Return if sensor is available."""
        return self.coordinator.last_update_success

    def _convert_usage(self, usage):
        """Convert usage based on the configuration and native unit."""
        usage_unit = self.coordinator.data.get("usageUnit")
        if usage_unit == "CF" and self.coordinator.config_entry.data.get("unit_type") == "G":
            self._attr_native_unit_of_measurement = "G"
            return usage * CF_TO_GALLON
        return usage


class SensusAnalyticsDailyUsageSensor(SensusAnalyticsSensorBase):
    """Representation of the daily usage sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the daily usage sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Daily Usage"
        self._attr_unique_id = f"{self._unique_id}_daily_usage"
        self._attr_native_unit_of_measurement = "CF"
        self._attr_icon = "mdi:water"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        daily_usage = self.coordinator.data.get("dailyUsage")
        return self._convert_usage(daily_usage)


class SensusAnalyticsUsageUnitSensor(SensusAnalyticsSensorBase):
    """Representation of the usage unit sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the usage unit sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Usage Unit"
        self._attr_unique_id = f"{self._unique_id}_usage_unit"
        self._attr_icon = "mdi:format-float"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("usageUnit")


class SensusAnalyticsMeterAddressSensor(SensusAnalyticsSensorBase):
    """Representation of the meter address sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the meter address sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Meter Address"
        self._attr_unique_id = f"{self._unique_id}_meter_address"
        self._attr_icon = "mdi:map-marker"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("meterAddress1")


class SensusAnalyticsLastReadSensor(SensusAnalyticsSensorBase):
    """Representation of the last read timestamp sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the last read sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Last Read"
        self._attr_unique_id = f"{self._unique_id}_last_read"
        self._attr_icon = "mdi:clock-time-nine"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        last_read_ts = self.coordinator.data.get("lastRead")
        if last_read_ts:
            # Convert milliseconds to seconds for timestamp
            return dt_util.utc_from_timestamp(last_read_ts / 1000).strftime("%Y-%m-%d %H:%M:%S")
        return None


class SensusAnalyticsBillingSensor(SensusAnalyticsSensorBase):
    """Representation of the billing status sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the billing sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Billing Active"
        self._attr_unique_id = f"{self._unique_id}_billing"
        self._attr_device_class = "power"
        self._attr_icon = "mdi:currency-usd"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("billing")


class SensusAnalyticsMeterLongitudeSensor(SensusAnalyticsSensorBase):
    """Representation of the meter longitude sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the meter longitude sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Meter Longitude"
        self._attr_unique_id = f"{self._unique_id}_meter_longitude"
        self._attr_native_unit_of_measurement = "°"
        self._attr_icon = "mdi:longitude"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("meterLong")


class SensusAnalyticsAlertCountSensor(SensusAnalyticsSensorBase):
    """Representation of the alert count sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the alert count sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Alert Count"
        self._attr_unique_id = f"{self._unique_id}_alert_count"
        self._attr_native_unit_of_measurement = "Alerts"
        self._attr_icon = "mdi:alert"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("alertCount")


class SensusAnalyticsMeterIdSensor(SensusAnalyticsSensorBase):
    """Representation of the meter ID sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the meter ID sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Meter ID"
        self._attr_unique_id = f"{self._unique_id}_meter_id"
        self._attr_icon = "mdi:account"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("meterId")


class SensusAnalyticsMeterLatitudeSensor(SensusAnalyticsSensorBase):
    """Representation of the meter latitude sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the meter latitude sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Meter Latitude"
        self._attr_unique_id = f"{self._unique_id}_meter_latitude"
        self._attr_native_unit_of_measurement = "°"
        self._attr_icon = "mdi:latitude"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("meterLat")


class SensusAnalyticsLatestReadUsageSensor(SensusAnalyticsSensorBase):
    """Representation of the latest read usage sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the latest read usage sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Latest Read Usage"
        self._attr_unique_id = f"{self._unique_id}_latest_read_usage"
        self._attr_native_unit_of_measurement = "CF"
        self._attr_icon = "mdi:water"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        latest_read_usage = self.coordinator.data.get("latestReadUsage")
        return self._convert_usage(latest_read_usage)


class SensusAnalyticsLatestReadTimeSensor(SensusAnalyticsSensorBase):
    """Representation of the latest read time sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the latest read time sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Latest Read Time"
        self._attr_unique_id = f"{self._unique_id}_latest_read_time"
        self._attr_icon = "mdi:clock-time-nine"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        latest_read_time_ts = self.coordinator.data.get("latestReadTime")
        if latest_read_time_ts:
            # Convert milliseconds to seconds for timestamp
            return dt_util.utc_from_timestamp(latest_read_time_ts / 1000).strftime("%Y-%m-%d %H:%M:%S")
        return None


class SensusAnalyticsBillingUsageSensor(SensusAnalyticsSensorBase):
    """Representation of the billing usage sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the billing usage sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Billing Usage"
        self._attr_unique_id = f"{self._unique_id}_billing_usage"
        self._attr_native_unit_of_measurement = "CF"
        self._attr_icon = "mdi:currency-usd"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        billing_usage = self.coordinator.data.get("billingUsage")
        return self._convert_usage(billing_usage)
