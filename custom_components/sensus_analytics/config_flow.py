"""Config flow for Sensus Analytics Integration."""

from __future__ import annotations

import logging

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import CONF_ACCOUNT_NUMBER, CONF_BASE_URL, CONF_METER_NUMBER, CONF_PASSWORD, CONF_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SensusAnalyticsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sensus Analytics Integration."""

    VERSION = 1

    def is_matching(self, other_flow):
        """Determine if this flow matches another flow."""
        # Implement matching logic if necessary
        return False  # Return False if you don't have specific matching logic

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            _LOGGER.debug("User input: %s", user_input)
            # Set a unique ID based on account and meter number
            unique_id = f"{user_input[CONF_ACCOUNT_NUMBER]}_{user_input[CONF_METER_NUMBER]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            # Validate the user input (e.g., test the connection)
            valid = await self._test_credentials(user_input)
            if valid:
                return self.async_create_entry(title="Sensus Analytics", data=user_input)
            errors["base"] = "auth"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_ACCOUNT_NUMBER): str,
                vol.Required(CONF_METER_NUMBER): str,
                vol.Required("unit_type", default="CF"): vol.In(["CF", "G"]),
                vol.Required("tier1_gallons", default=7480.52): cv.positive_float,
                vol.Required("tier1_price", default=0.0128): cv.positive_float,
                vol.Required("tier2_gallons", default=7480.52): cv.positive_float,
                vol.Required("tier2_price", default=0.0153): cv.positive_float,
                vol.Required("tier3_price", default=0.0202): cv.positive_float,
                vol.Required("service_fee", default=15.00): cv.positive_float,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def _test_credentials(self, user_input) -> bool:
        """Test if the provided credentials are valid."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{user_input[CONF_BASE_URL]}/j_spring_security_check",
                    data={
                        "j_username": user_input[CONF_USERNAME],
                        "j_password": user_input[CONF_PASSWORD],
                    },
                    allow_redirects=False,
                    timeout=10,
                ) as response:
                    _LOGGER.debug("Authentication response status: %s", response.status)
                    return response.status == 302
        except aiohttp.ClientError as error:
            _LOGGER.error("Error validating credentials: %s", error)
            return False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SensusAnalyticsOptionsFlow(config_entry)


class SensusAnalyticsOptionsFlow(config_entries.OptionsFlow):
    """Handle Sensus Analytics options."""

    def __init__(self, config_entry):
        """Initialize SensusAnalytics options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            _LOGGER.debug("User updated options: %s", user_input)
            # Update the entry with new options
            self.hass.config_entries.async_update_entry(self.config_entry, data=user_input)
            return self.async_create_entry(title="", data={})

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_BASE_URL,
                    default=self.config_entry.data.get(CONF_BASE_URL),
                ): str,
                vol.Required(
                    CONF_USERNAME,
                    default=self.config_entry.data.get(CONF_USERNAME),
                ): str,
                vol.Required(
                    CONF_PASSWORD,
                    default=self.config_entry.data.get(CONF_PASSWORD),
                ): str,
                vol.Required(
                    CONF_ACCOUNT_NUMBER,
                    default=self.config_entry.data.get(CONF_ACCOUNT_NUMBER),
                ): str,
                vol.Required(
                    CONF_METER_NUMBER,
                    default=self.config_entry.data.get(CONF_METER_NUMBER),
                ): str,
                vol.Required("unit_type", default=self.config_entry.data.get("unit_type", "CF")): vol.In(["CF", "G"]),
                vol.Required(
                    "tier1_gallons",
                    default=self.config_entry.data.get("tier1_gallons", 7480.52),
                ): cv.positive_float,
                vol.Required(
                    "tier1_price",
                    default=self.config_entry.data.get("tier1_price", 0.0128),
                ): cv.positive_float,
                vol.Required(
                    "tier2_gallons",
                    default=self.config_entry.data.get("tier2_gallons", 7480.52),
                ): cv.positive_float,
                vol.Required(
                    "tier2_price",
                    default=self.config_entry.data.get("tier2_price", 0.0153),
                ): cv.positive_float,
                vol.Required(
                    "tier3_price",
                    default=self.config_entry.data.get("tier3_price", 0.0202),
                ): cv.positive_float,
                vol.Required(
                    "service_fee",
                    default=self.config_entry.data.get("service_fee", 15.00),
                ): cv.positive_float,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
