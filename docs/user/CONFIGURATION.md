# Configuration Reference

## Setup Fields

| Option         | Required | Description                                                                        |
| -------------- | -------- | ---------------------------------------------------------------------------------- |
| Base URL       | Yes      | Sensus Analytics site URL, for example `https://<your_city>.sensus-analytics.com/` |
| Username       | Yes      | Sensus Analytics username                                                          |
| Password       | Yes      | Sensus Analytics password                                                          |
| Account Number | Yes      | Sensus Analytics account number                                                    |
| Meter Number   | Yes      | Water meter number                                                                 |
| Unit Type      | Yes      | Display usage as `CCF` or `gal`                                                    |
| Tier 1 Limit   | No       | Usage billed at the tier 1 price before tier 2 starts, in your display unit        |
| Tier 1 Price   | Yes      | Tier 1 price per display unit (per CCF or per gallon)                              |
| Tier 2 Limit   | No       | Usage billed at the tier 2 price before tier 3 starts, in your display unit        |
| Tier 2 Price   | No       | Tier 2 price per display unit                                                      |
| Tier 3 Price   | No       | Tier 3 price per display unit                                                      |
| Service Fee    | Yes      | Fixed service fee included in billing cost                                         |

The base URL is normalized with a trailing slash. If no scheme is provided, `https://` is assumed.

## Pricing

The billing cost and daily fee sensors are estimates based on the prices you enter.

- **Tier limits and prices use your display unit.** If Unit Type is `CCF`, enter your price per CCF and tier limits in CCF. If it is `gal`, use gallons. Easiest: pick the Unit Type your water bill uses, then copy its numbers as-is.
- **Tier limits are optional.** They are blank by default; leave a limit blank (or 0) when you don't need it.
- **One flat rate:** enter only Tier 1 Price and leave both tier limits blank (or 0).
- **Two tiers:** set Tier 1 Limit, Tier 1 Price, and Tier 2 Price. Leave Tier 2 Limit blank (or 0).
- **CF vs. CCF:** Sensus meters usually report in `CF` (cubic feet), shown by the Native Usage Unit sensor. The integration converts that to your display unit. 1 CCF is 100 cubic feet, or about 748 gallons.

## Options Flow

Use **Settings** -> **Devices & Services** -> **Sensus Analytics** -> **Configure** to change display and calculation settings:

| Option          | Default     | Description                                                                 |
| --------------- | ----------- | --------------------------------------------------------------------------- |
| Unit Type       | `CCF`       | Display usage as CCF or gallons                                             |
| Tier 1 Limit    | Blank       | Usage billed at the tier 1 price before tier 2 starts, in your display unit |
| Tier 1 Price    | `0.0128`    | Tier 1 price per display unit (per CCF or per gallon)                       |
| Tier 2 Limit    | Blank       | Usage billed at the tier 2 price before tier 3 starts, in your display unit |
| Tier 2 Price    | Blank       | Tier 2 price per display unit                                               |
| Tier 3 Price    | Blank       | Tier 3 price per display unit                                               |
| Service Fee     | `15.0`      | Fixed billing service fee                                                   |
| Update Interval | `5` minutes | Polling interval, 1 to 1440 minutes                                         |

Tier 1 Price, Service Fee, Unit Type, and Update Interval are required. Blank tier limit or price fields are treated as zero.

Changing Unit Type starts a new **Sensus Analytics water usage** statistic in the new unit (backfilled for 30 days). Select it again under **Settings** -> **Dashboards** -> **Energy** -> **Water consumption**. See [Energy Dashboard](../../README.md#energy-dashboard) in the README.

## Reconfiguration

Use **Reconfigure** when changing connection settings:

- Base URL
- Username
- Password
- Account Number
- Meter Number

Changing account or meter number also updates the config entry unique ID. The flow prevents configuring the same account and meter combination twice.

Reconfigure does not change the display unit or pricing. Use **Configure** (the options flow above) for those.

## When Data Shows Up

Sensus Analytics releases each day's readings at about local midnight, so a day's water appears in the sensors at the start of the next day. The **Sensus Analytics water usage** statistic used by the Energy dashboard is recorded at the hour the water was used, and late corrections replace the earlier numbers. See [When Does Data Show Up?](../../README.md#when-does-data-show-up) in the README for details.

## Actions

### `sensus_analytics.reload_data`

Refresh all loaded Sensus Analytics entries immediately. This does not make new data arrive sooner; it only fetches what Sensus Analytics has already published.

```yaml
action: sensus_analytics.reload_data
```

## Diagnostics

Diagnostics include config entry metadata, latest coordinator data, and the unit and last imported hour of the water usage statistic. Sensitive values are redacted:

- Base URL
- Username
- Password
- Account Number
- Meter Number
- Meter address
- Meter ID
- Meter latitude and longitude
