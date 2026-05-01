"""Sensor platform for Sensus Analytics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.sensus_analytics.const import PARALLEL_UPDATES as PARALLEL_UPDATES

from .water import ENTITY_DESCRIPTIONS, SensusAnalyticsSensor

if TYPE_CHECKING:
    from custom_components.sensus_analytics.data import SensusAnalyticsConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SensusAnalyticsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sensus Analytics sensor platform."""
    async_add_entities(
        SensusAnalyticsSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )
