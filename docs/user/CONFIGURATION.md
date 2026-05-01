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
| Tier 1 Gallons | No       | Gallons charged at the tier 1 price before tier 2 starts                           |
| Tier 1 Price   | Yes      | Tier 1 price per gallon                                                            |
| Tier 2 Gallons | No       | Gallons charged at the tier 2 price before tier 3 starts                           |
| Tier 2 Price   | No       | Tier 2 price per gallon                                                            |
| Tier 3 Price   | No       | Tier 3 price per gallon                                                            |
| Service Fee    | Yes      | Fixed service fee included in billing cost                                         |

The base URL is normalized with a trailing slash. If no scheme is provided, `https://` is assumed.

## Options Flow

The options flow controls display and calculation settings:

| Option          | Default     | Description                         |
| --------------- | ----------- | ----------------------------------- |
| Unit Type       | `CCF`       | Display usage as CCF or gallons     |
| Tier 1 Price    | `0.0128`    | Tier 1 price per gallon             |
| Service Fee     | `15.0`      | Fixed billing service fee           |
| Update Interval | `5` minutes | Polling interval, 1 to 1440 minutes |

Blank tier gallon or price fields are treated as zero.

## Reconfiguration

Use **Reconfigure** when changing connection settings:

- Base URL
- Username
- Password
- Account Number
- Meter Number

Changing account or meter number also updates the config entry unique ID. The flow prevents configuring the same account and meter combination twice.

## Services

### `sensus_analytics.reload_data`

Refresh all loaded Sensus Analytics entries immediately.

```yaml
service: sensus_analytics.reload_data
```

## Diagnostics

Diagnostics include config entry metadata and latest coordinator data. Sensitive values are redacted:

- Base URL
- Username
- Password
- Account Number
- Meter Number
- Meter address
- Meter ID
- Meter latitude and longitude
