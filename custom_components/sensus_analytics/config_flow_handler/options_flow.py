"""Options flow for Sensus Analytics."""

from __future__ import annotations

from typing import Any

from custom_components.sensus_analytics.config_flow_handler.schemas import get_options_schema
from homeassistant import config_entries


class SensusAnalyticsOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Sensus Analytics."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage Sensus Analytics options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=get_options_schema(defaults),
        )


__all__ = ["SensusAnalyticsOptionsFlow"]
