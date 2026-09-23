"""Repairs platform for Sensus Analytics.

This platform is intentionally present as a compatibility shim. The integration
does not currently raise fixable repair issues, but Home Assistant requires a
repairs platform module to implement ``async_create_fix_flow`` when the file
exists.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError


async def async_create_fix_flow(hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None) -> RepairsFlow:
    """Create a repair flow for a fixable issue."""
    raise HomeAssistantError(f"Unsupported repair issue: {issue_id}")
