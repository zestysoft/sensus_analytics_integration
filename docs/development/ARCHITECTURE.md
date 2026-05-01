# Architecture

The integration follows the current HACS integration blueprint structure while keeping only Sensus-specific runtime code.

## Runtime Flow

```text
Config flow -> Config entry data/options
            -> async_setup_entry
            -> SensusAnalyticsApiClient
            -> SensusAnalyticsDataUpdateCoordinator
            -> Sensor entities
```

Entities never call the API client directly. They read normalized data from the coordinator.

## Package Layout

```text
custom_components/sensus_analytics/
├── __init__.py                      # Setup, unload, reload, platform forwarding
├── api/
│   └── client.py                    # Async Sensus web endpoint client
├── config_flow.py                   # Home Assistant discovery shim
├── config_flow_handler/
│   ├── config_flow.py               # user, reconfigure, and reauth flows
│   ├── options_flow.py              # unit, pricing, and interval options
│   ├── schemas/                     # Voluptuous form schemas
│   └── validators/                  # Sanitization and credential validation
├── coordinator/
│   └── base.py                      # DataUpdateCoordinator
├── data.py                          # Typed config entry runtime data
├── diagnostics.py                   # Redacted diagnostics output
├── entity/
│   └── base.py                      # Shared coordinator entity behavior
├── sensor/
│   └── water.py                     # Water meter sensor descriptions/entities
├── service_actions/
│   └── __init__.py                  # reload_data service
├── services.yaml                    # Service metadata
└── translations/en.json             # Config, options, and entity strings
```

## Data Fetching

The API client logs in by posting to `j_spring_security_check`. Daily meter data is fetched from `water/widget/byPage`. Hourly usage and weather data is fetched from `water/usage/{account}/{meter}` for the previous local day.

Hourly data is best effort. Daily data failures fail the coordinator update; hourly communication failures are logged and the daily payload is still published.

## Entity Compatibility

Unique IDs intentionally preserve the original pattern:

```text
sensus_analytics_{entry_id}_{sensor_key}
```

This avoids duplicating existing entities for users upgrading from earlier releases.

## Tooling

Development tooling comes from `jpawlowski/hacs.integration_blueprint`:

- Devcontainer setup
- `script/` commands
- Ruff, Pyright, pytest, markdownlint, yamllint, prettier
- HACS and hassfest validation workflows
- Release Please
- Template sync
