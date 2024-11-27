# Sensus Analytics Integration

A custom Home Assistant integration to monitor your water usage from Sensus Analytics.

## Installation via HACS

### **Prerequisites**

- **HACS (Home Assistant Community Store)**: Make sure HACS is installed in your Home Assistant instance. If not, follow the [HACS Installation Guide](https://hacs.xyz/docs/installation/prerequisites).

### **Steps to Install**

1. **Open Home Assistant UI**

   Navigate to your Home Assistant instance in your web browser.

2. **Access HACS**

   - Click on "**HACS**" in the sidebar.

3. **Add Custom Repository**

   - In HACS, go to the "**Integrations**" tab.
   - Click on the "**⋮**" (three dots) menu in the top right corner and select "**Custom repositories**".

4. **Add the Sensus Analytics Repository**

   - **Repository URL**: `https://github.com/zestysoft/sensus_analytics_integration`
   - **Category**: Select "**Integration**" from the dropdown menu.
   - Click "**Add**".

5. **Install the Integration**

   - After adding the repository, return to the "**Integrations**" tab in HACS.
   - Search for "**Sensus Analytics Integration**".
   - Click on the integration and then click "**Install**".
   - Wait for HACS to download and install the integration. You should see a confirmation message once it's complete.

6. **Restart Home Assistant**

   - After installation, it's essential to restart Home Assistant to load the new integration.
   - Go to "**Configuration**" > "**Settings**" > "**System**" > "**Restart**".
   - Confirm the restart.

7. **Configure the Integration via Home Assistant UI**

   - Once Home Assistant has restarted, navigate to "**Configuration**" > "**Integrations**".
   - Click the "**+ Add Integration**" button in the bottom right corner.
   - Search for "**Sensus Analytics**" and select "**Sensus Analytics Integration**".
   - Follow the prompts to enter your credentials and settings:
     - **Base URL**: Enter the base URL for your Sensus Analytics API (e.g., `https://<your_city>.sensus-analytics.com/`).
     - **Username**: Your Sensus Analytics account username.
     - **Password**: Your Sensus Analytics account password.
     - **Account Number**: Your Sensus Analytics account number.
     - **Meter Number**: Your water meter number.
   - Click "**Submit**" to finalize the configuration.

## Features

- **Daily Usage**: Monitors daily water usage.
- **Usage Unit**: Displays the unit of measurement for water usage.
- **Meter Address**: Shows the address of the water meter.
- **Last Read**: Timestamp of the last meter reading.
- **Billing Active**: Indicates if billing is active.
- **Meter Longitude**: Longitude coordinate of the meter's location.
- **Alert Count**: Number of active alerts.
- **Meter ID**: Unique identifier for the water meter.
- **Meter Latitude**: Latitude coordinate of the meter's location.
- **Latest Read Usage**: Latest cumulative usage recorded by the meter.
- **Latest Read Time**: Timestamp of the latest reading.
- **Billing Usage**: Total usage amount that has been billed.

## Sensor Entities

Below are the sensor entities created by this integration:

- `sensor.sensus_analytics_daily_usage`: Daily water usage in cubic feet (CF).
- `sensor.sensus_analytics_usage_unit`: Unit of measurement for water usage.
- `sensor.sensus_analytics_meter_address`: Address of the water meter.
- `sensor.sensus_analytics_last_read`: Timestamp of the last meter reading.
- `sensor.sensus_analytics_billing_active`: Indicates if billing is active.
- `sensor.sensus_analytics_meter_longitude`: Longitude coordinate of the meter's location.
- `sensor.sensus_analytics_alert_count`: Number of active alerts.
- `sensor.sensus_analytics_meter_id`: Unique identifier for the water meter.
- `sensor.sensus_analytics_meter_latitude`: Latitude coordinate of the meter's location.
- `sensor.sensus_analytics_latest_read_usage`: Latest cumulative usage recorded by the meter.
- `sensor.sensus_analytics_latest_read_time`: Timestamp of the latest reading.
- `sensor.sensus_analytics_billing_usage`: Total usage amount that has been billed.

## License

[MIT License](LICENSE)
