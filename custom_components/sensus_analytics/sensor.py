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


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
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

    def __init__(
        self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._unique_id = f"{DOMAIN}_{entry.entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Unknown",
            model="Water Meter",
        )

    def _convert_usage(self, usage):
        """Convert usage based on the configuration and native unit."""
        if usage is None:
            return None
        usage_unit = self.coordinator.data.get("usageUnit")
        if (
            usage_unit == "CF"
            and self.coordinator.config_entry.data.get("unit_type") == "G"
        ):
            return round(float(usage) * CF_TO_GALLON)
        return usage

    def _get_usage_unit(self):
        """Determine the unit of measurement for usage sensors."""
        usage_unit = self.coordinator.data.get("usageUnit")
        if (
            usage_unit == "CF"
            and self.coordinator.config_entry.data.get("unit_type") == "G"
        ):
            return "G"
        return usage_unit


class SensusAnalyticsDailyUsageSensor(SensusAnalyticsSensorBase):
    """Representation of the daily usage sensor."""

    def __init__(
        self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry
    ):
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


# ... Repeat similar adjustments for other sensors ...

class SensusAnalyticsDailyFeeSensor(SensusAnalyticsSensorBase):
    """Representation of the daily fee sensor."""

    def __init__(
        self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry
    ):
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
