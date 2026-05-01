# Examples

## Notify on High Daily Usage

```yaml
automation:
  - alias: "Sensus high daily water usage"
    trigger:
      - platform: numeric_state
        entity_id: sensor.sensus_analytics_daily_usage
        above: 500
    action:
      - service: notify.notify
        data:
          message: "Daily water usage is {{ states('sensor.sensus_analytics_daily_usage') }} {{ state_attr('sensor.sensus_analytics_daily_usage', 'unit_of_measurement') }}."
```

## Refresh Data Before a Morning Report

```yaml
automation:
  - alias: "Refresh Sensus before morning report"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: sensus_analytics.reload_data
```

## Dashboard Card

```yaml
type: entities
title: Water Usage
entities:
  - sensor.sensus_analytics_daily_usage
  - sensor.sensus_analytics_meter_odometer
  - sensor.sensus_analytics_billing_usage
  - sensor.sensus_analytics_billing_cost
  - sensor.sensus_analytics_last_hour_usage
  - sensor.sensus_analytics_last_hour_temperature
```

## Billing Summary Template

```yaml
template:
  - sensor:
      - name: "Sensus Billing Summary"
        state: >
          {{ states('sensor.sensus_analytics_billing_usage') }}
          {{ state_attr('sensor.sensus_analytics_billing_usage', 'unit_of_measurement') }}
          / {{ states('sensor.sensus_analytics_billing_cost') }}
          {{ state_attr('sensor.sensus_analytics_billing_cost', 'unit_of_measurement') }}
```
