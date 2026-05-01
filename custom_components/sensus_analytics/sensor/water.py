"""Water usage sensors for Sensus Analytics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, tzinfo
from typing import Any

from custom_components.sensus_analytics.const import (
    CONF_SERVICE_FEE,
    CONF_TIER1_GALLONS,
    CONF_TIER1_PRICE,
    CONF_TIER2_GALLONS,
    CONF_TIER2_PRICE,
    CONF_TIER3_PRICE,
    CONF_UNIT_TYPE,
    DEFAULT_NAME,
    DEFAULT_SERVICE_FEE,
    DEFAULT_TIER1_PRICE,
    DEFAULT_UNIT_TYPE,
    UNIT_CCF,
    UNIT_GALLONS,
)
from custom_components.sensus_analytics.coordinator import SensusAnalyticsDataUpdateCoordinator
from custom_components.sensus_analytics.data import get_config_value
from custom_components.sensus_analytics.entity import SensusAnalyticsEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.util import dt as dt_util

CF_TO_GALLON = 7.48052
CF_PER_CCF = 100
GALLONS_PER_CCF = CF_TO_GALLON * CF_PER_CCF

ValueFn = Callable[[SensusAnalyticsDataUpdateCoordinator], Any]
UnitFn = Callable[[SensusAnalyticsDataUpdateCoordinator], str | None]
LastResetFn = Callable[[SensusAnalyticsDataUpdateCoordinator], datetime | None]


@dataclass(frozen=True, kw_only=True)
class SensusAnalyticsSensorEntityDescription(SensorEntityDescription):
    """Sensus Analytics sensor entity description."""

    label: str
    value_fn: ValueFn
    unit_fn: UnitFn | None = None
    last_reset_fn: LastResetFn | None = None


def _data(coordinator: SensusAnalyticsDataUpdateCoordinator) -> dict[str, Any]:
    """Return coordinator data as a dictionary."""
    return coordinator.data or {}


def _as_float(value: Any) -> float | None:
    """Convert a value to float when possible."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


def _normalized_unit(unit: Any) -> str | None:
    """Normalize Sensus usage unit names."""
    if unit is None:
        return None
    unit_str = str(unit).strip().upper()
    if unit_str in {"GAL", "GALLON", "GALLONS", "G"}:
        return UNIT_GALLONS
    if unit_str == UNIT_CCF:
        return UNIT_CCF
    if unit_str == "CF":
        return "CF"
    return unit_str


def _api_usage_unit(coordinator: SensusAnalyticsDataUpdateCoordinator) -> str | None:
    """Return the API-reported usage unit."""
    return _normalized_unit(_data(coordinator).get("usageUnit"))


def _configured_usage_unit(coordinator: SensusAnalyticsDataUpdateCoordinator) -> str:
    """Return the configured display usage unit."""
    configured = get_config_value(coordinator.config_entry, CONF_UNIT_TYPE, DEFAULT_UNIT_TYPE)
    if configured == UNIT_GALLONS:
        return UNIT_GALLONS
    return UNIT_CCF


def _convert_usage(
    coordinator: SensusAnalyticsDataUpdateCoordinator,
    usage: Any,
    source_unit: Any = None,
    target_unit: str | None = None,
) -> float | int | None:
    """Convert a Sensus usage value to the configured display unit."""
    usage_float = _as_float(usage)
    if usage_float is None:
        return None

    source = _normalized_unit(source_unit) or _api_usage_unit(coordinator)
    target = target_unit or _configured_usage_unit(coordinator)

    if source == target:
        return round(usage_float, 2)
    if source == "CF" and target == UNIT_GALLONS:
        return round(usage_float * CF_TO_GALLON)
    if source == "CF" and target == UNIT_CCF:
        return round(usage_float / CF_PER_CCF, 2)
    if source == UNIT_GALLONS and target == UNIT_CCF:
        return round(usage_float / GALLONS_PER_CCF, 2)
    if source == UNIT_CCF and target == UNIT_GALLONS:
        return round(usage_float * GALLONS_PER_CCF)

    return round(usage_float, 2)


def _convert_usage_to_gallons(
    coordinator: SensusAnalyticsDataUpdateCoordinator,
    usage: Any,
    source_unit: Any = None,
) -> float | None:
    """Convert a Sensus usage value to gallons for price calculations."""
    usage_float = _as_float(usage)
    if usage_float is None:
        return None

    source = _normalized_unit(source_unit) or _api_usage_unit(coordinator)
    if source == "CF":
        return usage_float * CF_TO_GALLON
    if source == UNIT_CCF:
        return usage_float * GALLONS_PER_CCF
    return usage_float


def _usage_unit(coordinator: SensusAnalyticsDataUpdateCoordinator) -> str:
    """Return the configured usage unit."""
    return _configured_usage_unit(coordinator)


def _currency(coordinator: SensusAnalyticsDataUpdateCoordinator) -> str:
    """Return Home Assistant's configured currency."""
    return coordinator.hass.config.currency


def _daily_usage(coordinator: SensusAnalyticsDataUpdateCoordinator) -> float | int | None:
    """Return daily usage."""
    return _convert_usage(coordinator, _data(coordinator).get("dailyUsage"))


def _native_usage_unit(coordinator: SensusAnalyticsDataUpdateCoordinator) -> str | None:
    """Return native usage unit."""
    return _data(coordinator).get("usageUnit")


def _last_read(coordinator: SensusAnalyticsDataUpdateCoordinator) -> datetime | None:
    """Return last read timestamp."""
    timestamp_ms = _as_float(_data(coordinator).get("lastRead"))
    if timestamp_ms is None:
        return None
    try:
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
    except OSError, ValueError:
        return None


def _meter_odometer(coordinator: SensusAnalyticsDataUpdateCoordinator) -> float | int | None:
    """Return cumulative meter usage."""
    return _convert_usage(coordinator, _data(coordinator).get("latestReadUsage"))


def _billing_usage(coordinator: SensusAnalyticsDataUpdateCoordinator) -> float | int | None:
    """Return billing usage."""
    return _convert_usage(coordinator, _data(coordinator).get("billingUsage"))


def _option_float(
    coordinator: SensusAnalyticsDataUpdateCoordinator,
    key: str,
    default: float = 0,
) -> float:
    """Return a float option/config value."""
    value = get_config_value(coordinator.config_entry, key, default)
    converted = _as_float(value)
    return default if converted is None else converted


def _calculate_tiered_cost(
    coordinator: SensusAnalyticsDataUpdateCoordinator,
    usage_gallons: float | None,
    *,
    include_service_fee: bool,
) -> float | None:
    """Calculate water cost from configured tier pricing."""
    if usage_gallons is None:
        return None

    tier1_gallons = _option_float(coordinator, CONF_TIER1_GALLONS)
    tier1_price = _option_float(coordinator, CONF_TIER1_PRICE, DEFAULT_TIER1_PRICE)
    tier2_gallons = _option_float(coordinator, CONF_TIER2_GALLONS)
    tier2_price = _option_float(coordinator, CONF_TIER2_PRICE)
    tier3_price = _option_float(coordinator, CONF_TIER3_PRICE)
    service_fee = _option_float(coordinator, CONF_SERVICE_FEE, DEFAULT_SERVICE_FEE)

    cost = service_fee if include_service_fee else 0
    if tier1_gallons == 0:
        cost += usage_gallons * tier1_price
    elif tier2_gallons == 0:
        cost += min(usage_gallons, tier1_gallons) * tier1_price
        if usage_gallons > tier1_gallons:
            cost += (usage_gallons - tier1_gallons) * tier2_price
    else:
        cost += min(usage_gallons, tier1_gallons) * tier1_price
        if usage_gallons > tier1_gallons:
            tier2_usage = min(usage_gallons - tier1_gallons, tier2_gallons)
            cost += tier2_usage * tier2_price
        if usage_gallons > tier1_gallons + tier2_gallons:
            cost += (usage_gallons - tier1_gallons - tier2_gallons) * tier3_price

    return round(cost, 2)


def _billing_cost(coordinator: SensusAnalyticsDataUpdateCoordinator) -> float | None:
    """Return billing cost."""
    usage_gallons = _convert_usage_to_gallons(coordinator, _data(coordinator).get("billingUsage"))
    return _calculate_tiered_cost(coordinator, usage_gallons, include_service_fee=True)


def _daily_fee(coordinator: SensusAnalyticsDataUpdateCoordinator) -> float | None:
    """Return daily fee."""
    usage_gallons = _convert_usage_to_gallons(coordinator, _data(coordinator).get("dailyUsage"))
    return _calculate_tiered_cost(coordinator, usage_gallons, include_service_fee=False)


def _local_tz(coordinator: SensusAnalyticsDataUpdateCoordinator) -> tzinfo:
    """Return Home Assistant's configured timezone."""
    return dt_util.get_time_zone(coordinator.hass.config.time_zone) or dt_util.DEFAULT_TIME_ZONE


def _hourly_entry_for_current_hour(coordinator: SensusAnalyticsDataUpdateCoordinator) -> dict[str, Any] | None:
    """Return the previous day's hourly entry matching the current local hour."""
    local_tz = _local_tz(coordinator)
    target_hour = datetime.now(local_tz).hour
    for entry in _data(coordinator).get("hourly_usage_data", []):
        timestamp_ms = _as_float(entry.get("timestamp"))
        if timestamp_ms is None:
            continue
        entry_time = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).astimezone(local_tz)
        if entry_time.hour == target_hour:
            return entry
    return None


def _last_hour_usage(coordinator: SensusAnalyticsDataUpdateCoordinator) -> float | int | None:
    """Return last-hour usage for the matching hour from the previous day."""
    entry = _hourly_entry_for_current_hour(coordinator)
    if entry is None:
        return None
    return _convert_usage(coordinator, entry.get("usage"), entry.get("usage_unit"))


def _last_hour_rainfall(coordinator: SensusAnalyticsDataUpdateCoordinator) -> float | None:
    """Return last-hour rainfall."""
    entry = _hourly_entry_for_current_hour(coordinator)
    return None if entry is None else _as_float(entry.get("rain"))


def _last_hour_temperature(coordinator: SensusAnalyticsDataUpdateCoordinator) -> float | None:
    """Return last-hour temperature."""
    entry = _hourly_entry_for_current_hour(coordinator)
    return None if entry is None else _as_float(entry.get("temp"))


def _last_hour_timestamp(coordinator: SensusAnalyticsDataUpdateCoordinator) -> datetime | None:
    """Return last-hour timestamp."""
    entry = _hourly_entry_for_current_hour(coordinator)
    if entry is None:
        return None
    timestamp_ms = _as_float(entry.get("timestamp"))
    if timestamp_ms is None:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)


def _start_of_local_day(coordinator: SensusAnalyticsDataUpdateCoordinator) -> datetime:
    """Return the start of the local day."""
    return dt_util.start_of_local_day()


def _start_of_billing_month(coordinator: SensusAnalyticsDataUpdateCoordinator) -> datetime:
    """Return the start of the current local month."""
    now = datetime.now(_local_tz(coordinator))
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _previous_hour(coordinator: SensusAnalyticsDataUpdateCoordinator) -> datetime:
    """Return the previous local hour."""
    now = datetime.now(_local_tz(coordinator))
    return now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)


ENTITY_DESCRIPTIONS: tuple[SensusAnalyticsSensorEntityDescription, ...] = (
    SensusAnalyticsSensorEntityDescription(
        key="daily_usage",
        label="Daily Usage",
        value_fn=_daily_usage,
        unit_fn=_usage_unit,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:water",
        last_reset_fn=_start_of_local_day,
    ),
    SensusAnalyticsSensorEntityDescription(
        key="usage_unit",
        label="Native Usage Unit",
        value_fn=_native_usage_unit,
    ),
    SensusAnalyticsSensorEntityDescription(
        key="meter_address",
        label="Meter Address",
        value_fn=lambda coordinator: _data(coordinator).get("meterAddress1"),
        icon="mdi:map-marker",
    ),
    SensusAnalyticsSensorEntityDescription(
        key="last_read",
        label="Last Read",
        value_fn=_last_read,
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-time-nine",
    ),
    SensusAnalyticsSensorEntityDescription(
        key="meter_longitude",
        label="Meter Longitude",
        value_fn=lambda coordinator: _data(coordinator).get("meterLong"),
        native_unit_of_measurement="°",
        icon="mdi:longitude",
    ),
    SensusAnalyticsSensorEntityDescription(
        key="meter_id",
        label="Meter ID",
        value_fn=lambda coordinator: _data(coordinator).get("meterId"),
        icon="mdi:account",
    ),
    SensusAnalyticsSensorEntityDescription(
        key="meter_latitude",
        label="Meter Latitude",
        value_fn=lambda coordinator: _data(coordinator).get("meterLat"),
        native_unit_of_measurement="°",
        icon="mdi:latitude",
    ),
    SensusAnalyticsSensorEntityDescription(
        key="meter_odometer",
        label="Meter Odometer",
        value_fn=_meter_odometer,
        unit_fn=_usage_unit,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:water",
    ),
    SensusAnalyticsSensorEntityDescription(
        key="billing_usage",
        label="Billing Usage",
        value_fn=_billing_usage,
        unit_fn=_usage_unit,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:water",
        last_reset_fn=_start_of_billing_month,
    ),
    SensusAnalyticsSensorEntityDescription(
        key="billing_cost",
        label="Billing Cost",
        value_fn=_billing_cost,
        unit_fn=_currency,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:currency-usd",
    ),
    SensusAnalyticsSensorEntityDescription(
        key="daily_fee",
        label="Daily Fee",
        value_fn=_daily_fee,
        unit_fn=_currency,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:currency-usd",
    ),
    SensusAnalyticsSensorEntityDescription(
        key="last_hour_usage",
        label="Last Hour Usage",
        value_fn=_last_hour_usage,
        unit_fn=_usage_unit,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:water",
        last_reset_fn=_previous_hour,
    ),
    SensusAnalyticsSensorEntityDescription(
        key="last_hour_rainfall",
        label="Last Hour Rainfall",
        value_fn=_last_hour_rainfall,
        native_unit_of_measurement="in",
        icon="mdi:weather-rainy",
    ),
    SensusAnalyticsSensorEntityDescription(
        key="last_hour_temperature",
        label="Last Hour Temperature",
        value_fn=_last_hour_temperature,
        native_unit_of_measurement="°F",
        icon="mdi:thermometer",
    ),
    SensusAnalyticsSensorEntityDescription(
        key="last_hour_timestamp",
        label="Last Hour Timestamp",
        value_fn=_last_hour_timestamp,
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-time-nine",
    ),
)


class SensusAnalyticsSensor(SensorEntity, SensusAnalyticsEntity):
    """Representation of a Sensus Analytics sensor."""

    entity_description: SensusAnalyticsSensorEntityDescription

    def __init__(
        self,
        coordinator: SensusAnalyticsDataUpdateCoordinator,
        entity_description: SensusAnalyticsSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entity_description)
        self._attr_name = f"{DEFAULT_NAME} {entity_description.label}"

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        if self.entity_description.unit_fn is not None:
            return self.entity_description.unit_fn(self.coordinator)
        return self.entity_description.native_unit_of_measurement

    @property
    def last_reset(self) -> datetime | None:
        """Return the last reset time."""
        if self.entity_description.last_reset_fn is None:
            return None
        return self.entity_description.last_reset_fn(self.coordinator)
