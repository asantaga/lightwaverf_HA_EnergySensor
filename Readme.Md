# Home Asisstant Sensor for the Lightwave RF Energy Monitor V1.6

Simple sensor component for Home Assistant which listens for the messages from the LightwaveRF Energy hub. This current implementation uses polling method, I may migrate it to a asynchronous approach in the future depending on how it perfroms

## Installation Instructions


### Manual Way
1. clone the repository to a local folder on your computer using git
``` git clone https://github.com/asantaga/lightwaverf_HA_EnergySensor.git ```
2. Copy the ```lightwaverf_energy``` directory within custom_components to your custom_components directory in your Hoome Assistant config directory
e.g.
``` cp -r custom_components/lightwave_energy <yourConfigDir>/custom_components```
3. Configure configuration.yaml as below
4. Ensure port 9761/UDP is open on your linux server. If you are using ufw then something like 
```ufw enable 9761/udp``` will do the trick



### HACS (https://custom-components.github.io/hacs/)
1. Add repository ```https://github.com/asantaga/lightwaverf_HA_EnergySensor``` as a integration and install 
voila easy
2. Configure configuration.yaml as below
3. Ensure port 9761/UDP is open on your linux server. If you are using ufw then something like 
```ufw enable 9761/udp``` will do the trick



Scan_interval is optional, defaults to every 30 seconds

***Remember Ensure port 9761/UDP is open for thi integration to work***

PR's / Issues welcome!

V 1.3 :  Migrated to new component model, breaking changes that yaml is now different

V 1.4 : Added support for HACS
V 1.5 : Added version number to manifest file
V 1.6 : Added PR which adds a socket close, hopefully fixes errors with ports still being open
