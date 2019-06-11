"""

Sensor Platform Device for LightwaveRF Electricity Monitor.

https://github.com/asantaga/wiserHomeAssistantPlatform
Angelo.santagata@gmail.com
"""

import json
import logging
import socket
import time

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)
DOMAIN = 'lightwaverf_energy'
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_SCAN_INTERVAL, default=60): cv.time_period
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """This function Sets up the sensor platform."""
    scan_interval = config.get(CONF_SCAN_INTERVAL).total_seconds()
    _LOGGER.info("scan interval={}".format(scan_interval))

    # scan_interval= config[DOMAIN][0][CONF_SCAN_INTERVAL].total_seconds()
    lightwave_devices = []

    lightwave_devices.append(LightwaveEnergy("CURRENT_USAGE", scan_interval))
    lightwave_devices.append(LightwaveEnergy("TODAY_USAGE", scan_interval))
    add_devices(lightwave_devices)


""" 

LightwaveEnergy platform class

"""


class LightwaveEnergy(Entity):
    """Primary class for Lightwave Energy."""

    def __init__(self, sensor_type, scan_interval):
        """Initialize the sensor."""
        _LOGGER.info("Lightwave Energy Init , scan interval={}"
                     .format(scan_interval))
        self.sensor_type = sensor_type
        self.serial = ""
        self.mac = ""
        self.current_usage = ""
        self.today_usage = ""
        self.lightwave_energy_data = None
        self.scan_interval = scan_interval
        self._updatets = time.time()

    def update(self):
        """Function called when HA asks for an update."""
        _LOGGER.info("Lightwave Energy Monitor update")
        if (time.time() - self._updatets) >= (self.scan_interval - 1):
            _LOGGER.info("waiting for Data from Lightwave Energy Monitor")
            data = None
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('0.0.0.0', 9761))
            sock.settimeout(10.0)  # Wait a Max of 10 seconds
            # wait for an energy update
            try:
                data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
                _LOGGER.info("Data received % {}".format(data))
            except socket.timeout as ex:
                _LOGGER.error("No data received from lightwaveRF energy monitor {}"
                              .format(ex))
            # Convert to JSON
            if data is None:
                self.lightwave_energy_data = json.loads(data[2:])
                self.serial = self.lightwave_energy_data.get('serial')
                self.mac = self.lightwave_energy_data.get("mac")
                self.current_usage = self.lightwave_energy_data.get('cUse')
                self.today_usage = self.lightwave_energy_data.get('todUse')
                _LOGGER.debug("Lightwave_Energy skipping update")
            self._updatets = time.time()
        else:
            _LOGGER.info("Lightwave_Energy skipping update")

    @property
    def icon(self):
        """Returns a simple flash/lightning bolt as an icon."""
        return "mdi:flash"

    @property
    def name(self):
        """Returns the name of the sensor."""
        if self.sensor_type == 'CURRENT_USAGE':
            return "Electricity Current Usage (W)"
        return "Electricity Energy Today Usage (kWh)"

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    @property
    def unit_of_measurement(self):
        """UOM is either W or kWh."""
        if self.sensor_type == 'CURRENT_USAGE':
            return 'W'
        return 'kWh'

    @property
    def state(self):
        """Get current state of sensor."""
        if self.sensor_type == 'CURRENT_USAGE':
            return self.current_usage
        try:
            return int(self.today_usage) / 1000
        except ValueError:
            _LOGGER.info("Lightwave_Energy got value error - data not yet received ")
            return ""  # If we get value error its because the data isnt populated yet