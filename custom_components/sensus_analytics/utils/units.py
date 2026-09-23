"""Water volume unit helpers shared by the sensors and the statistics import."""

from __future__ import annotations

from typing import Any

from custom_components.sensus_analytics.const import UNIT_CCF, UNIT_GALLONS

UNIT_CUBIC_FEET = "CF"

CF_TO_GALLON = 7.48052
CF_PER_CCF = 100
GALLONS_PER_CCF = CF_TO_GALLON * CF_PER_CCF


def as_float(value: Any) -> float | None:
    """Convert a value to float when possible."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


def normalized_unit(unit: Any) -> str | None:
    """Normalize Sensus usage unit names."""
    if unit is None:
        return None
    unit_str = str(unit).strip().upper()
    if unit_str in {"GAL", "GALLON", "GALLONS", "G"}:
        return UNIT_GALLONS
    return unit_str


def convert_volume(value: float, source: str | None, target: str) -> float | None:
    """Convert an unrounded volume between normalized units.

    Returns None when there is no known conversion between the two units.
    """
    if source == target:
        return value
    if source == UNIT_CUBIC_FEET and target == UNIT_GALLONS:
        return value * CF_TO_GALLON
    if source == UNIT_CUBIC_FEET and target == UNIT_CCF:
        return value / CF_PER_CCF
    if source == UNIT_GALLONS and target == UNIT_CCF:
        return value / GALLONS_PER_CCF
    if source == UNIT_CCF and target == UNIT_GALLONS:
        return value * GALLONS_PER_CCF
    return None
