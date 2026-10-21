## Example YAML
``` yaml
   lightwaverf_energy:
      scan_interval: 30
```

## Configuration options

| Key  | Type  | Required  | Desc |
|:---|:---|:---|:---|
|  `scan_interval` |  number | False  | Scan Interval, defaults to 30  |

## Changelog

**1.9** - Fixed readings lagging real time. Unread UDP packets queued up between polls so each update read a stale value; updates now drain the queue and use the newest reading.
