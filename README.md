# Sensus Analytics Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

A custom Home Assistant integration that monitors water usage from Sensus Analytics.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/zestysoft/sensus_analytics_integration?quickstart=1)

## Features

- Daily water usage
- Native and configurable usage units
- Meter address, ID, latitude, and longitude
- Last meter read timestamp
- Meter odometer and billing usage
- Estimated billing cost and daily usage fee from tiered pricing
- Last-hour usage, rainfall, temperature, and timestamp from the previous day
- UI setup, reconfiguration, reauthentication, and options flow
- Manual `sensus_analytics.reload_data` service

**This integration sets up the following platform.**

| Platform | Description                                                               |
| -------- | ------------------------------------------------------------------------- |
| `sensor` | Water usage, meter details, billing estimates, and hourly comparison data |

## Quick Start

### Step 1: Install the Integration

This integration requires [HACS](https://hacs.xyz/) to be installed.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zestysoft&repository=sensus_analytics_integration&category=integration)

Then:

1. Click **Download** to install the integration.
2. Restart Home Assistant.

<details>
<summary><strong>Manual Installation</strong></summary>

1. Download the `custom_components/sensus_analytics/` folder from this repository.
2. Copy it to your Home Assistant `custom_components/` directory.
3. Restart Home Assistant.

</details>

### Step 2: Add and Configure the Integration

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=sensus_analytics)

The setup flow asks for:

| Name           | Required | Description                                                                             |
| -------------- | -------- | --------------------------------------------------------------------------------------- |
| Base URL       | Yes      | Your Sensus Analytics site URL, for example `https://<your_city>.sensus-analytics.com/` |
| Username       | Yes      | Your Sensus Analytics username                                                          |
| Password       | Yes      | Your Sensus Analytics password                                                          |
| Account Number | Yes      | Your Sensus Analytics account number                                                    |
| Meter Number   | Yes      | Your water meter number                                                                 |
| Unit Type      | Yes      | Display usage as `CCF` or `gal`                                                         |
| Tier 1 Gallons | No       | Gallons charged at tier 1 before tier 2 starts                                          |
| Tier 1 Price   | Yes      | Tier 1 price per gallon                                                                 |
| Tier 2 Gallons | No       | Gallons charged at tier 2 before tier 3 starts                                          |
| Tier 2 Price   | No       | Tier 2 price per gallon                                                                 |
| Tier 3 Price   | No       | Tier 3 price per gallon                                                                 |
| Service Fee    | Yes      | Fixed service fee for billing estimates                                                 |

### Step 3: Adjust Options

After setup, use **Settings** -> **Devices & Services** -> **Sensus Analytics** -> **Configure** to update:

- Display unit
- Tiered pricing
- Service fee
- Update interval

Use **Reconfigure** to update the URL, credentials, account number, or meter number.

## Sensor Entities

- `sensor.sensus_analytics_daily_usage`
- `sensor.sensus_analytics_usage_unit`
- `sensor.sensus_analytics_meter_address`
- `sensor.sensus_analytics_last_read`
- `sensor.sensus_analytics_meter_longitude`
- `sensor.sensus_analytics_meter_id`
- `sensor.sensus_analytics_meter_latitude`
- `sensor.sensus_analytics_meter_odometer`
- `sensor.sensus_analytics_billing_usage`
- `sensor.sensus_analytics_billing_cost`
- `sensor.sensus_analytics_daily_fee`
- `sensor.sensus_analytics_last_hour_usage`
- `sensor.sensus_analytics_last_hour_rainfall`
- `sensor.sensus_analytics_last_hour_temperature`
- `sensor.sensus_analytics_last_hour_timestamp`

## Services

### `sensus_analytics.reload_data`

Manually refresh data for all loaded Sensus Analytics entries.

```yaml
service: sensus_analytics.reload_data
```

## Development

This repository follows the current `jpawlowski/hacs.integration_blueprint` structure for development tooling.

Useful commands:

```bash
script/setup/bootstrap
script/lint-check
script/type-check
script/test
script/hassfest
script/check
```

## Support

If you like the integration, how about buying me a coffee?

[![Buy me a coffee!](https://www.buymeacoffee.com/assets/img/custom_images/black_img.png)](https://www.buymeacoffee.com/zestysoft)

## License

[Apache 2.0](LICENSE)

[commits-shield]: https://img.shields.io/github/commit-activity/y/zestysoft/sensus_analytics_integration.svg?style=for-the-badge
[commits]: https://github.com/zestysoft/sensus_analytics_integration/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/zestysoft/sensus_analytics_integration.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40zestysoft-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/zestysoft/sensus_analytics_integration.svg?style=for-the-badge
[releases]: https://github.com/zestysoft/sensus_analytics_integration/releases
