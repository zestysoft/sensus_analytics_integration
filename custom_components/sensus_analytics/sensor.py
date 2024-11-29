"""Sensor platform for the Sensus Analytics Integration."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DEFAULT_NAME, DOMAIN

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
            SensusAnalyticsBillingUsageSensor(coordinator, entry),
            SensusAnalyticsBillingCostSensor(coordinator, entry),
            SensusAnalyticsDailyFeeSensor(coordinator, entry),
        ],
        True,
    )


class UsageConversionMixin:
    """Mixin to provide usage conversion."""

    # pylint: disable=too-few-public-methods
    def _convert_usage(self, usage):
        """Convert usage based on configuration and native unit."""
        if usage is None:
            return None
        usage_unit = self.coordinator.data.get("usageUnit")
        if usage_unit == "CF" and self.coordinator.config_entry.data.get("unit_type") == "G":
            try:
                return round(float(usage) * CF_TO_GALLON)
            except (ValueError, TypeError):
                return None
        return usage


class DynamicUnitSensorBase(UsageConversionMixin, CoordinatorEntity, SensorEntity):
    """Base class for sensors with dynamic units."""

    def __init__(self, coordinator, entry):
        """Initialize the dynamic unit sensor base."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.entry = entry
        self._unique_id = f"{DOMAIN}_{entry.entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Unknown",
            model="Water Meter",
        )

    def _get_usage_unit(self):
        """Determine the unit of measurement for usage sensors."""
        usage_unit = self.coordinator.data.get("usageUnit")
        if usage_unit == "CF" and self.coordinator.config_entry.data.get("unit_type") == "G":
            return "G"
        return usage_unit

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._get_usage_unit()


class StaticUnitSensorBase(UsageConversionMixin, CoordinatorEntity, SensorEntity):
    """Base class for sensors with static units."""

    def __init__(self, coordinator, entry, unit=None, device_class=None):
        """Initialize the static unit sensor base."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.entry = entry
        self._unique_id = f"{DOMAIN}_{entry.entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Unknown",
            model="Water Meter",
        )
        if unit:
            self._attr_native_unit_of_measurement = unit
        if device_class:
            self._attr_device_class = device_class


class SensusAnalyticsDailyUsageSensor(DynamicUnitSensorBase):
    """Representation of the daily usage sensor."""

    def __init__(self, coordinator, entry):
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


class SensusAnalyticsUsageUnitSensor(StaticUnitSensorBase):
    """Representation of the usage unit sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the usage unit sensor."""
        super().__init__(coordinator, entry, unit=None)
        self._attr_name = f"{DEFAULT_NAME} Native Usage Unit"
        self._attr_unique_id = f"{self._unique_id}_usage_unit"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("usageUnit")


class SensusAnalyticsMeterAddressSensor(StaticUnitSensorBase):
    """Representation of the meter address sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the meter address sensor."""
        super().__init__(coordinator, entry, unit=None)
        self._attr_name = f"{DEFAULT_NAME} Meter Address"
        self._attr_unique_id = f"{self._unique_id}_meter_address"
        self._attr_icon = "mdi:map-marker"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("meterAddress1")


class SensusAnalyticsLastReadSensor(StaticUnitSensorBase):
    """Representation of the last read timestamp sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the last read sensor."""
        super().__init__(coordinator, entry, unit=None, device_class=SensorDeviceClass.TIMESTAMP)
        self._attr_name = f"{DEFAULT_NAME} Last Read"
        self._attr_unique_id = f"{self._unique_id}_last_read"
        self._attr_icon = "mdi:clock-time-nine"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        last_read_ts = self.coordinator.data.get("lastRead")
        if last_read_ts:
            # Convert milliseconds to seconds for timestamp
            try:
                return dt_util.utc_from_timestamp(last_read_ts / 1000)
            except (ValueError, TypeError):
                return None
        return None


class SensusAnalyticsMeterLongitudeSensor(StaticUnitSensorBase):
    """Representation of the meter longitude sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the meter longitude sensor."""
        super().__init__(coordinator, entry, unit="°")
        self._attr_name = f"{DEFAULT_NAME} Meter Longitude"
        self._attr_unique_id = f"{self._unique_id}_meter_longitude"
        self._attr_icon = "mdi:longitude"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("meterLong")


class SensusAnalyticsMeterIdSensor(StaticUnitSensorBase):
    """Representation of the meter ID sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the meter ID sensor."""
        super().__init__(coordinator, entry, unit=None)
        self._attr_name = f"{DEFAULT_NAME} Meter ID"
        self._attr_unique_id = f"{self._unique_id}_meter_id"
        self._attr_icon = "mdi:account"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("meterId")


class SensusAnalyticsMeterLatitudeSensor(StaticUnitSensorBase):
    """Representation of the meter latitude sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the meter latitude sensor."""
        super().__init__(coordinator, entry, unit="°")
        self._attr_name = f"{DEFAULT_NAME} Meter Latitude"
        self._attr_unique_id = f"{self._unique_id}_meter_latitude"
        self._attr_icon = "mdi:latitude"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("meterLat")


class SensusAnalyticsLatestReadUsageSensor(DynamicUnitSensorBase):
    """Representation of the latest read usage sensor."""

    def __init__(self, coordinator, entry):
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


class SensusAnalyticsBillingUsageSensor(DynamicUnitSensorBase):
    """Representation of the billing usage sensor."""

    def __init__(self, coordinator, entry):
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


class SensusAnalyticsBillingCostSensor(StaticUnitSensorBase):
    """Representation of the billing cost sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the billing cost sensor."""
        super().__init__(coordinator, entry, unit="USD")
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

    def _calculate_cost(self, usage_gallons):
        """Calculate the billing cost based on tiers and service fee."""
        tier1_gallons = self.coordinator.config_entry.data.get("tier1_gallons") or 0
        tier1_price = self.coordinator.config_entry.data.get("tier1_price") or 0
        tier2_gallons = self.coordinator.config_entry.data.get("tier2_gallons") or 0
        tier2_price = self.coordinator.config_entry.data.get("tier2_price") or 0
        tier3_price = self.coordinator.config_entry.data.get("tier3_price") or 0
        service_fee = self.coordinator.config_entry.data.get("service_fee") or 0

        cost = service_fee
        if usage_gallons is not None:
            if tier1_gallons == 0:
                # No tier 1 limit, all usage is charged at tier 1 price
                cost += usage_gallons * tier1_price
            elif tier2_gallons == 0:
                # No tier 2 limit, calculate for tier 1 and tier 2
                if usage_gallons <= tier1_gallons:
                    cost += usage_gallons * tier1_price
                else:
                    cost += tier1_gallons * tier1_price
                    cost += (usage_gallons - tier1_gallons) * tier2_price
            elif tier3_price > 0:
                # Calculate for all three tiers
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


class SensusAnalyticsDailyFeeSensor(StaticUnitSensorBase):
    """Representation of the daily fee sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the daily fee sensor."""
        super().__init__(coordinator, entry, unit="USD")
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

    def _calculate_daily_fee(self, usage_gallons):
        """Calculate the daily fee based on tiers."""
        tier1_gallons = self.coordinator.config_entry.data.get("tier1_gallons") or 0
        tier1_price = self.coordinator.config_entry.data.get("tier1_price") or 0
        tier2_gallons = self.coordinator.config_entry.data.get("tier2_gallons") or 0
        tier2_price = self.coordinator.config_entry.data.get("tier2_price") or 0
        tier3_price = self.coordinator.config_entry.data.get("tier3_price") or 0

        cost = 0
        if usage_gallons is not None:
            if tier1_gallons == 0:
                # No tier 1 limit, all usage is charged at tier 1 price
                cost += usage_gallons * tier1_price
            elif tier2_gallons == 0:
                # No tier 2 limit, calculate for tier 1 and tier 2
                if usage_gallons <= tier1_gallons:
                    cost += usage_gallons * tier1_price
                else:
                    cost += tier1_gallons * tier1_price
                    cost += (usage_gallons - tier1_gallons) * tier2_price
            elif tier3_price > 0:
                # Calculate for all three tiers
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
