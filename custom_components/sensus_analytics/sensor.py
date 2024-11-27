"""Sensor platform for the Sensus Analytics Integration."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, DEFAULT_NAME
from .coordinator import SensusAnalyticsDataUpdateCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SensusAnalyticsSensor(coordinator, entry)], True)

class SensusAnalyticsSensor(SensorEntity):
    """Representation of a Sensus Analytics Sensor."""

    def __init__(self, coordinator: SensusAnalyticsDataUpdateCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._name = f"{DEFAULT_NAME} Usage"
        self._state = None
        self._attributes = {}
        self._unique_id = f"{DOMAIN}_{entry.entry_id}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get('dailyUsage')
        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self.coordinator.data

    async def async_update(self):
        """Request an update from the coordinator."""
        await self.coordinator.async_request_refresh()
