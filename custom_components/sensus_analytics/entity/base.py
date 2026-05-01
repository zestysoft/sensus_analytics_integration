"""Base entity class for the Sensus Analytics integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.sensus_analytics.const import ATTRIBUTION, CONF_BASE_URL, DEFAULT_NAME, DOMAIN
from custom_components.sensus_analytics.coordinator import SensusAnalyticsDataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription


class SensusAnalyticsEntity(CoordinatorEntity[SensusAnalyticsDataUpdateCoordinator]):
    """Base entity class for Sensus Analytics entities."""

    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: SensusAnalyticsDataUpdateCoordinator,
        entity_description: EntityDescription,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = f"{DOMAIN}_{coordinator.config_entry.entry_id}_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    coordinator.config_entry.entry_id,
                ),
            },
            name=DEFAULT_NAME,
            manufacturer="Sensus",
            model="Water Meter",
            configuration_url=coordinator.config_entry.data.get(CONF_BASE_URL),
        )
