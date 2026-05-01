"""Custom runtime data types for the Sensus Analytics integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import SensusAnalyticsApiClient
    from .coordinator import SensusAnalyticsDataUpdateCoordinator


type SensusAnalyticsConfigEntry = ConfigEntry[SensusAnalyticsData]


@dataclass
class SensusAnalyticsData:
    """Runtime data stored on each config entry."""

    client: SensusAnalyticsApiClient
    coordinator: SensusAnalyticsDataUpdateCoordinator
    integration: Integration


def get_config_value(
    entry: SensusAnalyticsConfigEntry,
    key: str,
    default: Any = None,
) -> Any:
    """Return an option value with config entry data as the fallback."""
    return entry.options.get(key, entry.data.get(key, default))
