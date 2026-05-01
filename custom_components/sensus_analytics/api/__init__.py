"""
API package for sensus_analytics.

Architecture:
    Three-layer data flow: Entities → Coordinator → API Client.
    Only the coordinator should call the API client. Entities must never
    import or call the API client directly.

Exception hierarchy:
    SensusAnalyticsApiClientError (base)
    ├── SensusAnalyticsApiClientCommunicationError (network/timeout)
    └── SensusAnalyticsApiClientAuthenticationError (401/403)

Coordinator exception mapping:
    ApiClientAuthenticationError → ConfigEntryAuthFailed (triggers reauth)
    ApiClientCommunicationError → UpdateFailed (auto-retry)
    ApiClientError             → UpdateFailed (auto-retry)
"""

from .client import (
    SensusAnalyticsApiClient,
    SensusAnalyticsApiClientAuthenticationError,
    SensusAnalyticsApiClientCommunicationError,
    SensusAnalyticsApiClientError,
)

__all__ = [
    "SensusAnalyticsApiClient",
    "SensusAnalyticsApiClientAuthenticationError",
    "SensusAnalyticsApiClientCommunicationError",
    "SensusAnalyticsApiClientError",
]
