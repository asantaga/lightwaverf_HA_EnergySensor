# Home Asisstant Sensor for the Lightwave RF Energy Monitor V1.1

Simple sensor component for Home Assistant which listens for the messages from the LightwaveRF Energy hub. This current implementation uses polling method, I may migrate it to a asynchronous approach in the future depending on how it perfroms

## Installation Instructions

1. Copy sensor/lightwave_energy.py into your custom_components directory
2. Configure configuration.yaml
   ```
   sensor lightwaveEnergy:
     - platform: lightwave_energy
   ```

PR's / Issues welcome!
