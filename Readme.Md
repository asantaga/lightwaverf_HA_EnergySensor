# Home Assistant integration for the Lightwave RF Energy Monitor V2.0.0

Home Assistant integration that listens for the readings the LightwaveRF energy monitor broadcasts on your network. It creates a device with two sensors, current usage (W) and today's usage (kWh), which can both be added to Home Assistant's Energy dashboard.

The sensors show as unknown until the first reading arrives, and as unavailable if the monitor has been silent for 5 minutes.

## Installation

### HACS
1. In HACS, add the custom repository ```https://github.com/asantaga/lightwaverf_HA_EnergySensor``` as an integration and install it.
2. Restart Home Assistant.

### Manual
1. Clone the repository: ``` git clone https://github.com/asantaga/lightwaverf_HA_EnergySensor.git ```
2. Copy the integration into your Home Assistant config directory: ``` cp -r custom_components/lightwaverf_energy <yourConfigDir>/custom_components```
3. Restart Home Assistant.

### Network
The monitor broadcasts on port 9761/UDP, so that port must be open on the Home Assistant host. With ufw: ```ufw allow 9761/udp```. If Home Assistant runs in Docker, use host networking, since broadcasts don't reach a bridged container.

## Configuration

Go to **Settings > Devices & services > Add integration** and choose **Lightwave Energy Monitor**. The only setting is the update interval in seconds (default 30), which you can change later with the integration's **Configure** button. Only one listener can run, so the integration can be added once.

If more than one monitor broadcasts on your network, the integration uses the first one it hears and ignores the rest.

### Upgrading from YAML
Earlier versions were set up in configuration.yaml:
```
lightwaverf_energy:
  scan_interval: 30
```
Version 2.0.0 imports this automatically on the first start, keeping your entity IDs and history. Home Assistant then shows a repair notice; remove the YAML and restart to clear it. The old `sensor: - platform: lightwaverf_energy` form is imported the same way.

PR's / Issues welcome!

V 1.3 :  Migrated to new component model, breaking changes that yaml is now different

V 1.4 : Added support for HACS
V 1.5 : Added version number to manifest file
V 1.6 : Added PR which adds a socket close, hopefully fixes errors with ports still being open
v 1.7.1 :  Getting back into it after a long break, dot release getting things working agian
v1.8 : Working again
v1.9 : Fixed readings lagging real time (by ~70 min on one install). The monitor broadcasts more often than the sensor polls, so unread UDP packets queued up in the socket buffer and each poll read a stale one. Each update now drains the queue and uses the newest reading.
v2.0.0 : Version 2.0.0 is set up from the UI (Settings > Devices & services) and creates a device with two sensors. Existing YAML is imported automatically, keeping entity IDs and history, and Home Assistant then shows a repair notice asking you to remove the YAML. The sensors are now proper Home Assistant sensors, so they keep long-term statistics and appear in the Energy dashboard. They show as unknown before the first reading and as unavailable if the monitor goes quiet for 5 minutes. The update interval now really sets how often readings are taken, and can be changed under the integration's Configure button. Updates never block waiting for a packet, packets that aren't meter readings are ignored, and the listener locks on to one monitor if neighbours' monitors are also broadcasting. Requires Home Assistant 2024.12 or later.
