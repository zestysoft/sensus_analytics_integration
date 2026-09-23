# Getting Started

This guide covers installation and first setup for the Sensus Analytics Integration.

## Prerequisites

- Home Assistant 2026.4.0 or newer
- HACS installed
- A working Sensus Analytics account
- Your Sensus Analytics account number and meter number

## Installation

### Via HACS

1. Open HACS in Home Assistant.
2. Go to **Integrations**.
3. Add this custom repository:
   `https://github.com/zestysoft/sensus_analytics_integration`
4. Set the category to **Integration**.
5. Download **Sensus Analytics Integration**.
6. Restart Home Assistant.

### Manual Installation

1. Download the latest release from GitHub.
2. Copy `custom_components/sensus_analytics/` into your Home Assistant `custom_components/` directory.
3. Restart Home Assistant.

## Initial Setup

1. Go to **Settings** -> **Devices & Services**.
2. Click **+ Add Integration**.
3. Search for **Sensus Analytics**.
4. Enter your Sensus Analytics URL, credentials, account number, meter number, display unit, and pricing options.

The integration validates credentials during setup. If authentication fails, check the base URL, username, and password.

## Created Entities

The integration creates one water meter device with sensors for:

- Daily usage
- Native usage unit
- Meter address, ID, latitude, and longitude
- Last read timestamp
- Meter odometer
- Billing usage, billing cost, and daily fee
- Last-hour usage, rainfall, temperature, and timestamp from the previous day

## Options

Use **Configure** on the integration entry to update:

- Display unit (`CCF` or `gal`)
- Tiered price settings
- Service fee
- Polling interval

Use **Reconfigure** to update the Sensus Analytics URL, credentials, account number, or meter number.

## Troubleshooting

Enable debug logging when investigating setup or update problems:

```yaml
logger:
  default: warning
  logs:
    custom_components.sensus_analytics: debug
```

Diagnostics can be downloaded from the integration device page. Credentials, account number, meter number, address, and meter location are redacted.
