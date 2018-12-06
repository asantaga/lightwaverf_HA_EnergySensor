"""
Sensor Platform Device for LightwaveRF Electricity Monitor

https://github.com/asantaga/wiserHomeAssistantPlatform
Angelo.santagata@gmail.com
"""

import socket
import logging
import json
from homeassistant.helpers.entity import Entity


_LOGGER = logging.getLogger(__name__)

DOMAIN = "lightwaverf_energy"



def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the sensor platform."""
    lightwaveDevices=[]
    lightwaveDevices.append(LightwaveEnergy("CURRENT_USAGE")   )
    lightwaveDevices.append(LightwaveEnergy("TODAY_USAGE")   )
    add_devices(lightwaveDevices)
    

class LightwaveEnergy(Entity):
    def __init__(self, sensorType):
            
        """Initialize the sensor."""
        _LOGGER.info('Lightwave Energy Init')
        self.sensorType=sensorType
        self.serial=""
        self.mac=""
        self.currentUsage=""
        self.todayUsage=""
        self.lightwaveEnergyData=None


    def update(self):
        data=None
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', 9761))
        sock.settimeout(10.0) # Wait a Max of 10 seconds
        # wait for an energy update
        _LOGGER.info ("waiting for Data from Lightwave Energy Monitor")
        try:
            data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
            _LOGGER.info ("Data received % {}".format(data))
        except socket.timeout as ex:
            _LOGGER.error("No data received from lightwaveRF energy monitor {}".format(ex))
        # Convert to JSON
        if data!=None:
            self.lightwaveEnergyData=json.loads(data[2:])
            self.serial=self.lightwaveEnergyData.get("serial")
            self.mac=self.lightwaveEnergyData.get("mac")
            self.currentUsage=self.lightwaveEnergyData.get('cUse')
            self.todayUsage=self.lightwaveEnergyData.get('todUse')
    @property
    def icon(self):
        return "mdi:flash"

    @property
    def name(self):
        if (self.sensorType=="CURRENT_USAGE"):
            return "Electricity Current Usage (W)"
        return "Electricity Energy Today Usage (kWh)"

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    @property
    def unit_of_measurement(self):
        if (self.sensorType=="CURRENT_USAGE"):
            return "W"
        return "kWh"

    @property
    def state(self):
        if (self.sensorType=="CURRENT_USAGE"):
          return self.currentUsage
        try:
          return int(self.todayUsage)/1000
        except ValueError as ex:
          return ""   # If we get value error its because the data isnt populated yet
