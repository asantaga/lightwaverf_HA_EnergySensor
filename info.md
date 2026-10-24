Home Assistant integration for the LightwaveRF energy monitor. It creates a device with two sensors, current usage (W) and today's usage (kWh), which can both be used in the Energy dashboard.

## Set-up

After installing, restart Home Assistant and add **Lightwave Energy Monitor** under **Settings > Devices & services**. Port 9761/UDP must be open on the Home Assistant host. Existing YAML configuration is imported automatically.

| Option | Default | Description |
|:---|:---|:---|
| Update interval | 30 | Seconds between readings |

## Changelog

**2.0.0** - Version 2.0.0 is set up from the UI (Settings > Devices & services) and creates a device with two sensors. Existing YAML is imported automatically, keeping entity IDs and history, and Home Assistant then shows a repair notice asking you to remove the YAML. The sensors are now proper Home Assistant sensors, so they keep long-term statistics and appear in the Energy dashboard. They show as unknown before the first reading and as unavailable if the monitor goes quiet for 5 minutes. The update interval now really sets how often readings are taken, and can be changed under the integration's Configure button. Updates never block waiting for a packet, packets that aren't meter readings are ignored, and the listener locks on to one monitor if neighbours' monitors are also broadcasting. Requires Home Assistant 2024.12 or later.

**1.9** - Fixed readings lagging real time. Unread UDP packets queued up between polls so each update read a stale value; updates now drain the queue and use the newest reading.
