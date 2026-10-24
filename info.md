## Example YAML
``` yaml
   lightwaverf_energy:
      scan_interval: 30
```

## Configuration options

| Key  | Type  | Required  | Desc |
|:---|:---|:---|:---|
|  `scan_interval` |  number | False  | Scan Interval, defaults to 30  |

Creates two sensors: current usage (W) and today's usage (kWh). Both can be
used in Home Assistant's Energy dashboard. Port 9761/UDP must be open.

## Changelog

**1.10** - Sensors are now proper Home Assistant sensors, so they keep long-term statistics and appear in the Energy dashboard. Updates no longer block for 10 seconds when no packet is waiting, packets that aren't meter readings are ignored, and values show as unknown (not blank) before the first reading. `scan_interval` is now validated and defaults to 30 seconds, as documented. Requires Home Assistant 2023.1 or later.

**1.9** - Fixed readings lagging real time. Unread UDP packets queued up between polls so each update read a stale value; updates now drain the queue and use the newest reading.
