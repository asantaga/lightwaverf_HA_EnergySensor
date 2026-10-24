"""
Sensor Platform Device for LightwaveRF Electricity Monitor.

https://github.com/asantaga/lightwaverf_HA_EnergySensor
Angelo.santagata@gmail.com
"""
import json
import logging
import socket
import time

from homeassistant.const import CONF_SCAN_INTERVAL, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)
DATA_KEY = "lightwaverf_energy"
PORT = 9761


class LightwaveEnergyHub:
    """Shared UDP listener and cache for Lightwave energy data."""

    def __init__(self, scan_interval):
        """Initialize the shared hub."""
        self.scan_interval = scan_interval
        self.serial = ""
        self.mac = ""
        self.current_usage = ""
        self.today_usage = ""
        self.last_update = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(10.0)  # Wait a max of 10 seconds
        self._configure_socket()

    def _configure_socket(self):
        """Bind the UDP socket once for the whole integration."""
        for opt_name in ("SO_REUSEADDR", "SO_REUSEPORT"):
            opt = getattr(socket, opt_name, None)
            if opt is not None:
                try:
                    self.sock.setsockopt(socket.SOL_SOCKET, opt, 1)
                except OSError as err:
                    _LOGGER.debug("Unable to set %s on UDP socket: %s", opt_name, err)

        try:
            self.sock.bind(("0.0.0.0", PORT))
        except OSError as err:
            self.sock.close()
            _LOGGER.error("Unable to bind UDP listener on port %s: %s", PORT, err)
            raise

    def update(self):
        """Read the next packet if the scan interval has elapsed."""
        if (time.time() - self.last_update) < (self.scan_interval - 1):
            _LOGGER.debug("Lightwave energy update skipped; scan interval not elapsed")
            return

        data = None
        # The monitor broadcasts more often than we poll, so packets queue up in
        # the socket buffer. Drain the backlog and keep only the newest packet,
        # otherwise readings lag real time by however long the queue is.
        dropped = 0
        self.sock.setblocking(False)
        try:
            while True:
                try:
                    packet, _ = self.sock.recvfrom(1024)
                except BlockingIOError:
                    break
                if data is not None:
                    dropped += 1
                data = packet
        except OSError as err:
            _LOGGER.error("Failed draining LightwaveRF energy monitor data: %s", err)
        finally:
            self.sock.settimeout(10.0)
        if dropped:
            _LOGGER.debug("Discarded %s stale Lightwave energy packets", dropped)

        if data is None:
            _LOGGER.info("Waiting for data from Lightwave energy monitor on UDP %s", PORT)
            try:
                data, _ = self.sock.recvfrom(1024)
            except socket.timeout as err:
                _LOGGER.error("No data received from LightwaveRF energy monitor: %s", err)
            except OSError as err:
                _LOGGER.error("Failed reading LightwaveRF energy monitor data: %s", err)
        if data is not None:
            _LOGGER.info("Data received %s", data)

        if data is not None:
            lightwave_energy_data = json.loads(data[2:])
            self.serial = lightwave_energy_data.get("serial", "")
            self.mac = lightwave_energy_data.get("mac", "")
            self.current_usage = lightwave_energy_data.get("cUse", "")
            self.today_usage = lightwave_energy_data.get("todUse", "")

        self.last_update = time.time()

    def close(self, _event=None):
        """Close the UDP listener during shutdown."""
        if self.sock is None:
            return
        self.sock.close()
        self.sock = None


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Configure the sensor platform for home assistant."""
    scan_interval = hass.data[DATA_KEY]
    _LOGGER.info("scan interval= %s", scan_interval)
    hub = LightwaveEnergyHub(scan_interval)
    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, hub.close)
    lightwave_devices = [
        LightwaveEnergy("CURRENT_USAGE", hub),
        LightwaveEnergy("TODAY_USAGE", hub),
    ]
    add_devices(lightwave_devices)


class LightwaveEnergy(Entity):
    """Primary class for Lightwave Energy."""

    def __init__(self, sensor_type, hub):
        """Initialize the sensor."""
        _LOGGER.info("Lightwave Energy Init, sensor_type=%s", sensor_type)
        self.sensor_type = sensor_type
        self.hub = hub

    @property
    def unique_id(self):
        """Return the stable Home Assistant entity identifier."""
        if self.sensor_type == "CURRENT_USAGE":
            return "lightwaverf_energy_current_usage"
        return "lightwaverf_energy_today_usage"

    def update(self):
        """Update Lightwave State."""
        _LOGGER.info("Lightwave Energy Monitor update")
        self.hub.update()

    @property
    def icon(self):
        """Icon is a lightning bolt."""
        return "mdi:flash"

    @property
    def name(self):
        """Sensor name."""
        if self.sensor_type == "CURRENT_USAGE":
            return "Electricity Current Usage (W)"
        return "Electricity Energy Today Usage (kWh)"

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    @property
    def unit_of_measurement(self):
        """UOM is either W or kWh."""
        if self.sensor_type == "CURRENT_USAGE":
            return "W"
        return "kWh"

    @property
    def device_class(self):
        """Return the Home Assistant device class."""
        if self.sensor_type == "CURRENT_USAGE":
            return "power"
        return "energy"

    @property
    def state_class(self):
        """Return the Home Assistant state class."""
        if self.sensor_type == "CURRENT_USAGE":
            return "measurement"
        return "total_increasing"

    @property
    def state(self):
        """Get current state of sensor."""
        if self.sensor_type == "CURRENT_USAGE":
            return self.hub.current_usage
        try:
            return int(self.hub.today_usage) / 1000
        except ValueError:
            _LOGGER.info(
                "Lightwave_Energy got value error - data not yet " "#received "
            )
            # If we get value error its because the data isnt populated yet
            return ""
