"""Sensor platform for the Sensus Analytics Integration."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
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
            SensusAnalyticsMeterLongitudeSensor(coordinator, entry),
            SensusAnalyticsMeterIdSensor(coordinator, entry),
            SensusAnalyticsMeterLatitudeSensor(coordinator, entry),
            SensusAnalyticsLatestReadUsageSensor(coordinator, entry),
            SensusAnalyticsLatestReadTimeSensor(coordinator, entry),
            SensusAnalyticsBillingUsageSensor(coordinator, entry),
            SensusAnalyticsBillingCostSensor(coordinator, entry),
            SensusAnalyticsDailyFeeSensor(coordinator, entry),
        ],
        True,
    )


class SensusAnalyticsSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Sensus Analytics Sensors."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._unique_id = f"{DOMAIN}_{entry.entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Unknown",
            model="Water Meter",
        )
        self.entry = entry

    def _convert_usage(self, usage):
        """Convert usage based on the configuration and native unit."""
        if usage is None:
            return None
        usage_unit = self.coordinator.data.get("usageUnit")
        if usage_unit == "CF" and self.coordinator.config_entry.data.get("unit_type") == "G":
            return round(float(usage) * CF_TO_GALLON)
        return usage

    def _get_usage_unit(self):
        """Determine the unit of measurement for usage sensors."""
        usage_unit = self.coordinator.data.get("usageUnit")
        if usage_unit == "CF" and self.coordinator.config_entry.data.get("unit_type") == "G":
            return "G"
        return usage_unit


class SensusAnalyticsDailyUsageSensor(SensusAnalyticsSensorBase):
    """Representation of the daily usage sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the daily usage sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Daily Usage"
        self._attr_unique_id = f"{self._unique_id}_daily_usage"
        self._attr_icon = "mdi:water"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        daily_usage = self.coordinator.data.get("dailyUsage")
        return self._convert_usage(daily_usage)

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._get_usage_unit()


class SensusAnalyticsUsageUnitSensor(SensusAnalyticsSensorBase):
    """Representation of the usage unit sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the usage unit sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Native Usage Unit"
        self._attr_unique_id = f"{self._unique_id}_usage_unit"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("usageUnit")

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return None  # No unit of measurement for this sensor


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

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return None  # No unit of measurement for this sensor


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

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return None  # No unit of measurement for this sensor


class SensusAnalyticsMeterLongitudeSensor(SensusAnalyticsSensorBase):
    """Representation of the meter longitude sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the meter longitude sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Meter Longitude"
        self._attr_unique_id = f"{self._unique_id}_meter_longitude"
        self._attr_icon = "mdi:longitude"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("meterLong")

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return "°"


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

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return None  # No unit of measurement for this sensor


class SensusAnalyticsMeterLatitudeSensor(SensusAnalyticsSensorBase):
    """Representation of the meter latitude sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the meter latitude sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Meter Latitude"
        self._attr_unique_id = f"{self._unique_id}_meter_latitude"
        self._attr_icon = "mdi:latitude"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("meterLat")

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return "°"


class SensusAnalyticsLatestReadUsageSensor(SensusAnalyticsSensorBase):
    """Representation of the latest read usage sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the latest read usage sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Latest Read Usage"
        self._attr_unique_id = f"{self._unique_id}_latest_read_usage"
        self._attr_icon = "mdi:water"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        latest_read_usage = self.coordinator.data.get("latestReadUsage")
        return self._convert_usage(latest_read_usage)

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._get_usage_unit()


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

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return None  # No unit of measurement for this sensor


class SensusAnalyticsBillingUsageSensor(SensusAnalyticsSensorBase):
    """Representation of the billing usage sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the billing usage sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Billing Usage"
        self._attr_unique_id = f"{self._unique_id}_billing_usage"
        self._attr_icon = "mdi:water"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        billing_usage = self.coordinator.data.get("billingUsage")
        return self._convert_usage(billing_usage)

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._get_usage_unit()


class SensusAnalyticsBillingCostSensor(SensusAnalyticsSensorBase):
    """Representation of the billing cost sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the billing cost sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Billing Cost"
        self._attr_unique_id = f"{self._unique_id}_billing_cost"
        self._attr_icon = "mdi:currency-usd"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        usage = self.coordinator.data.get("billingUsage")
        if usage is None:
            return None
        usage_gallons = self._convert_usage(usage)
        return self._calculate_cost(usage_gallons)

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return "USD"

    def _calculate_cost(self, usage_gallons):
        """Calculate the billing cost based on tiers and service fee."""
        tier1_gallons = self.coordinator.config_entry.data.get("tier1_gallons")
        tier1_price = self.coordinator.config_entry.data.get("tier1_price")
        tier2_gallons = self.coordinator.config_entry.data.get("tier2_gallons")
        tier2_price = self.coordinator.config_entry.data.get("tier2_price")
        tier3_price = self.coordinator.config_entry.data.get("tier3_price")
        service_fee = self.coordinator.config_entry.data.get("service_fee")

        cost = service_fee
        if usage_gallons <= tier1_gallons:
            cost += usage_gallons * tier1_price
        elif usage_gallons <= tier1_gallons + tier2_gallons:
            cost += tier1_gallons * tier1_price
            cost += (usage_gallons - tier1_gallons) * tier2_price
        else:
            cost += tier1_gallons * tier1_price
            cost += tier2_gallons * tier2_price
            cost += (usage_gallons - tier1_gallons - tier2_gallons) * tier3_price

        return round(cost, 2)


class SensusAnalyticsDailyFeeSensor(SensusAnalyticsSensorBase):
    """Representation of the daily fee sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the daily fee sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Daily Fee"
        self._attr_unique_id = f"{self._unique_id}_daily_fee"
        self._attr_icon = "mdi:currency-usd"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        usage = self.coordinator.data.get("dailyUsage")
        if usage is None:
            return None
        usage_gallons = self._convert_usage(usage)
        return self._calculate_daily_fee(usage_gallons)

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return "USD"

    def _calculate_daily_fee(self, usage_gallons):
        """Calculate the daily fee based on tiers."""
        tier1_gallons = self.coordinator.config_entry.data.get("tier1_gallons")
        tier1_price = self.coordinator.config_entry.data.get("tier1_price")
        tier2_gallons = self.coordinator.config_entry.data.get("tier2_gallons")
        tier2_price = self.coordinator.config_entry.data.get("tier2_price")
        tier3_price = self.coordinator.config_entry.data.get("tier3_price")

        cost = 0
        if usage_gallons <= tier1_gallons:
            cost += usage_gallons * tier1_price
        elif usage_gallons <= tier1_gallons + tier2_gallons:
            cost += tier1_gallons * tier1_price
            cost += (usage_gallons - tier1_gallons) * tier2_price
        else:
            cost += tier1_gallons * tier1_price
            cost += tier2_gallons * tier2_price
            cost += (usage_gallons - tier1_gallons - tier2_gallons) * tier3_price

        return round(cost, 2)
