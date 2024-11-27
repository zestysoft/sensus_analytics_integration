"""Config flow for Sensus Analytics Integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_BASE_URL, CONF_USERNAME, CONF_PASSWORD, CONF_ACCOUNT_NUMBER, CONF_METER_NUMBER

_LOGGER = logging.getLogger(__name__)

class SensusAnalyticsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sensus Analytics Integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Validate the user input here
            # For now, we'll accept any input
            return self.async_create_entry(title="Sensus Analytics", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_BASE_URL): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Required(CONF_ACCOUNT_NUMBER): str,
            vol.Required(CONF_METER_NUMBER): str,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
