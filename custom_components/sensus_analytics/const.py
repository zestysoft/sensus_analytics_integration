"""Constants for the Sensus Analytics integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "sensus_analytics"
DEFAULT_NAME = "Sensus Analytics"
ATTRIBUTION = "Data provided by Sensus Analytics"

PARALLEL_UPDATES = 1

CONF_BASE_URL = "base_url"
CONF_ACCOUNT_NUMBER = "account_number"
CONF_METER_NUMBER = "meter_number"
CONF_UNIT_TYPE = "unit_type"
CONF_TIER1_GALLONS = "tier1_gallons"
CONF_TIER1_PRICE = "tier1_price"
CONF_TIER2_GALLONS = "tier2_gallons"
CONF_TIER2_PRICE = "tier2_price"
CONF_TIER3_PRICE = "tier3_price"
CONF_SERVICE_FEE = "service_fee"
CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"

DEFAULT_UNIT_TYPE = "CCF"
DEFAULT_TIER1_PRICE = 0.0128
DEFAULT_SERVICE_FEE = 15.0
DEFAULT_UPDATE_INTERVAL_MINUTES = 5

UNIT_CCF = "CCF"
UNIT_GALLONS = "gal"

SERVICE_RELOAD_DATA = "reload_data"
