"""Input sanitization utilities for Sensus config flows."""

from __future__ import annotations

from custom_components.sensus_analytics.const import CONF_ACCOUNT_NUMBER, CONF_BASE_URL, CONF_METER_NUMBER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME


def sanitize_base_url(base_url: str) -> str:
    """Normalize a Sensus Analytics base URL."""
    sanitized = base_url.strip()
    if sanitized and not sanitized.startswith(("http://", "https://")):
        sanitized = f"https://{sanitized}"
    return f"{sanitized.rstrip('/')}/"


def sanitize_config_input(user_input: dict) -> dict:
    """Sanitize all config input fields."""
    sanitized = user_input.copy()

    if CONF_BASE_URL in sanitized:
        sanitized[CONF_BASE_URL] = sanitize_base_url(str(sanitized[CONF_BASE_URL]))
    if CONF_USERNAME in sanitized:
        sanitized[CONF_USERNAME] = str(sanitized[CONF_USERNAME]).strip()
    if CONF_PASSWORD in sanitized:
        sanitized[CONF_PASSWORD] = str(sanitized[CONF_PASSWORD])
    if CONF_ACCOUNT_NUMBER in sanitized:
        sanitized[CONF_ACCOUNT_NUMBER] = str(sanitized[CONF_ACCOUNT_NUMBER]).strip()
    if CONF_METER_NUMBER in sanitized:
        sanitized[CONF_METER_NUMBER] = str(sanitized[CONF_METER_NUMBER]).strip()

    return sanitized


__all__ = [
    "sanitize_base_url",
    "sanitize_config_input",
]
