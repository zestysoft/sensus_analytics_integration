"""Config flow for the Sensus Analytics integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.sensus_analytics.config_flow_handler.schemas import (
    get_reauth_schema,
    get_reconfigure_schema,
    get_user_schema,
)
from custom_components.sensus_analytics.config_flow_handler.validators import validate_credentials
from custom_components.sensus_analytics.const import (
    CONF_ACCOUNT_NUMBER,
    CONF_METER_NUMBER,
    DEFAULT_NAME,
    DOMAIN,
    LOGGER,
)
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME
from homeassistant.loader import async_get_loaded_integration

if TYPE_CHECKING:
    from custom_components.sensus_analytics.config_flow_handler.options_flow import SensusAnalyticsOptionsFlow

ERROR_MAP = {
    "SensusAnalyticsApiClientAuthenticationError": "auth",
    "SensusAnalyticsApiClientCommunicationError": "connection",
}


class SensusAnalyticsConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sensus Analytics."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SensusAnalyticsOptionsFlow:
        """Return the options flow."""
        from custom_components.sensus_analytics.config_flow_handler.options_flow import (  # noqa: PLC0415
            SensusAnalyticsOptionsFlow,
        )

        return SensusAnalyticsOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial user setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                user_input = await validate_credentials(self.hass, user_input)
            except Exception as exception:  # noqa: BLE001
                errors["base"] = self._map_exception_to_error(exception)
            else:
                unique_id = f"{user_input[CONF_ACCOUNT_NUMBER]}_{user_input[CONF_METER_NUMBER]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=DEFAULT_NAME,
                    data=user_input,
                )

        integration = async_get_loaded_integration(self.hass, DOMAIN)
        assert integration.documentation is not None, "Integration documentation URL is not set in manifest.json"

        return self.async_show_form(
            step_id="user",
            data_schema=get_user_schema(user_input),
            errors=errors,
            description_placeholders={
                "documentation_url": integration.documentation,
            },
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration of all connection settings."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                user_input = await validate_credentials(self.hass, user_input)
            except Exception as exception:  # noqa: BLE001
                errors["base"] = self._map_exception_to_error(exception)
            else:
                unique_id = f"{user_input[CONF_ACCOUNT_NUMBER]}_{user_input[CONF_METER_NUMBER]}"
                for existing_entry in self._async_current_entries(include_ignore=False):
                    if existing_entry.entry_id != entry.entry_id and existing_entry.unique_id == unique_id:
                        return self.async_abort(reason="already_configured")
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=unique_id,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=get_reconfigure_schema(entry.data),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle reauthentication when credentials are invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle reauthentication confirmation."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            merged_input = {**entry.data, **user_input}
            try:
                merged_input = await validate_credentials(self.hass, merged_input)
            except Exception as exception:  # noqa: BLE001
                errors["base"] = self._map_exception_to_error(exception)
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data=merged_input,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=get_reauth_schema(entry.data),
            errors=errors,
            description_placeholders={
                "username": entry.data.get(CONF_USERNAME, ""),
            },
        )

    def _map_exception_to_error(self, exception: Exception) -> str:
        """Map API exceptions to user-facing error keys."""
        LOGGER.warning("Error in config flow: %s", exception)
        exception_name = type(exception).__name__
        return ERROR_MAP.get(exception_name, "unknown")


__all__ = ["SensusAnalyticsConfigFlowHandler"]
