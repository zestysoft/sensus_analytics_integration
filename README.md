# Sensus Analytics Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

A custom Home Assistant integration that monitors water usage from Sensus Analytics.

## Features

- Daily water usage
- Native and configurable usage units
- Meter address, ID, latitude, and longitude
- Last meter read timestamp
- Meter odometer and billing usage
- Estimated billing cost and daily usage fee from tiered pricing
- Last-hour usage, rainfall, temperature, and timestamp from the previous day
- Hourly water usage in the Energy dashboard, recorded on the correct day and at the correct hour
- UI setup, reconfiguration, reauthentication, and options flow
- Manual `sensus_analytics.reload_data` action

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
| Tier 1 Limit   | No       | Usage billed at the tier 1 price before tier 2 starts, in your display unit             |
| Tier 1 Price   | Yes      | Tier 1 price per display unit (per CCF or per gallon)                                   |
| Tier 2 Limit   | No       | Usage billed at the tier 2 price before tier 3 starts, in your display unit             |
| Tier 2 Price   | No       | Tier 2 price per display unit                                                           |
| Tier 3 Price   | No       | Tier 3 price per display unit                                                           |
| Service Fee    | Yes      | Fixed service fee for billing estimates                                                 |

### Pricing

The billing cost and daily fee sensors are estimates based on the prices you enter.

- **Tier limits and prices use your display unit.** If Unit Type is `CCF`, enter your price per CCF and tier limits in CCF. If it is `gal`, use gallons. Easiest: pick the Unit Type your water bill uses, then copy its numbers as-is.
- **Tier limits are optional.** They are blank by default; leave a limit blank (or 0) when you don't need it.
- **One flat rate:** enter only Tier 1 Price and leave both tier limits blank (or 0).
- **Two tiers:** set Tier 1 Limit, Tier 1 Price, and Tier 2 Price. Leave Tier 2 Limit blank (or 0).
- **CF vs. CCF:** Sensus meters usually report in `CF` (cubic feet), shown by the Native Usage Unit sensor. The integration converts that to your display unit. 1 CCF is 100 cubic feet, or about 748 gallons.

### Step 3: Adjust Options

After setup, use **Settings** -> **Devices & Services** -> **Sensus Analytics** -> **Configure** to update:

- Display unit
- Tiered pricing
- Service fee
- Update interval

Use **Reconfigure** to update the URL, credentials, account number, or meter number.

## Sensor Entities

- `sensor.sensus_analytics_daily_usage`
- `sensor.sensus_analytics_native_usage_unit`
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

## Energy Dashboard

The integration imports Sensus hourly usage into Home Assistant's long-term statistics as **Sensus Analytics water usage**. Each hour's water is recorded on the **same day and at the same hour it was actually used**, not when Home Assistant received it. For example, water used at 7 AM on Monday shows up in the Energy dashboard at 7 AM on Monday, even though Sensus only publishes it after midnight. The Energy dashboard's daily and hourly charts match the Sensus portal.

To use it (or to switch over after updating from an older version):

1. Go to **Settings** -> **Dashboards** -> **Energy** -> **Water consumption**.
2. Add **Sensus Analytics water usage**.
3. If **Sensus Analytics Last Hour Usage** is listed, remove it. Keeping both counts every gallon twice.

Good to know:

- **It backfills 30 days.** The first import also fills in the 30 days before yesterday, so the Energy dashboard has history right away. If Home Assistant is offline for a few days, the missing days are filled in when it comes back.
- **Data still arrives after midnight, but it lands on the correct day and hour.** Yesterday stays empty until Sensus publishes it (around midnight), then fills in with each hour in its right place. Late corrections replace the earlier numbers.
- **The statistic uses your display unit.** Changing Unit Type starts a new statistic (backfilled the same way), so pick **Sensus Analytics water usage** again in the Energy settings afterwards.
- **With more than one meter**, each statistic's name ends with its meter number.
- **The Last Hour sensors stay.** They still show the same clock hour from the previous day and remain useful for automations.

## When Does Data Show Up?

Water data from Sensus Analytics is not real time, so it is normal for the sensors to lag behind your actual usage.

- **Data arrives once a day.** Sensus Analytics usually holds the day's readings and releases the whole previous day at about local midnight. Small late corrections can trickle in over the next few hours (updates have been seen between about 1 AM and 8 AM).
- **Sensors record data when it arrives.** Home Assistant can't backdate sensor history, so a day's water appears in the sensors at the start of the next day.
- **The Energy dashboard shows water on the correct day and hour.** The [Sensus Analytics water usage](#energy-dashboard) statistic is backdated to when the water was used: Monday's 7 AM shower shows up at 7 AM on Monday, not on Tuesday. It appears once Sensus publishes the day, around midnight.
- **Daily Usage and Last Read describe the previous day.**
- **The Last Hour sensors show the same clock hour from the previous day.**
- **Reloading won't make data arrive sooner.** The `sensus_analytics.reload_data` action only fetches what Sensus Analytics has already published.

## Actions

### `sensus_analytics.reload_data`

Manually refresh data for all loaded Sensus Analytics entries.

```yaml
action: sensus_analytics.reload_data
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
