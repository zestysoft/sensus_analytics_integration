# Getting Started

This guide covers installation and first setup for the Sensus Analytics Integration.

## Prerequisites

- Home Assistant 2026.4.0 or newer
- HACS installed
- A Sensus Analytics username and password that work on your Sensus site's own login page (logins that go through a city billing website, known as single sign-on, are not supported yet)
- Your Sensus Analytics account number and meter number

## Installation

### Via HACS

Requires HACS 2.0.5 or newer.

The quickest way is the **Open your Home Assistant instance** button in the [README](../../README.md#step-1-install-the-integration). To add the repository by hand:

1. Open **HACS** in Home Assistant.
2. Open the **⋮** menu in the top right and choose **Custom repositories**.
3. Enter `https://github.com/zestysoft/sensus_analytics_integration`, set the type to **Integration**, and click **Add**.
4. Search HACS for **Sensus Analytics Integration** and open it.
5. Click **Download**.
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

Use **Reconfigure** to update the Sensus Analytics URL, credentials, account number, or meter number. Display unit and pricing are changed through **Configure**.

## When Data Shows Up

Sensus Analytics releases each day's readings at about local midnight, so don't expect the sensors to update in real time. See [When Does Data Show Up?](../../README.md#when-does-data-show-up) for details.

## Troubleshooting

Enable debug logging when investigating setup or update problems:

```yaml
logger:
  default: warning
  logs:
    custom_components.sensus_analytics: debug
```

To download diagnostics, go to **Settings** -> **Devices & Services** -> **Sensus Analytics**, open the **⋮** menu on the integration entry, and choose **Download diagnostics**. Credentials, account number, meter number, address, and meter location are redacted.
