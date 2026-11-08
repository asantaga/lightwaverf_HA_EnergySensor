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

**1.10** - Fixed core `lightwave` lights/switches responding slowly. The hub sends command ACKs to port 9761, which this sensor also listened on, so it swallowed them and the lights integration retried each command for ~15s. The sensor now binds to the broadcast address (meter data is broadcast, ACKs are unicast) and ignores any packet that is not meter data.

**1.9** - Fixed readings lagging real time. Unread UDP packets queued up between polls so each update read a stale value; updates now drain the queue and use the newest reading.
