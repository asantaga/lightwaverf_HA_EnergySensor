"""
Sensor Platform Device for LightwaveRF Electricity Monitor.

https://github.com/asantaga/lightwaverf_HA_EnergySensor
Angelo.santagata@gmail.com
"""
import json
import logging
import socket
import time

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP,
    UnitOfEnergy,
    UnitOfPower,
)

_LOGGER = logging.getLogger(__name__)
DATA_KEY = "lightwaverf_energy"
PORT = 9761
# Warn (once) if the monitor has been silent for this many seconds.
NO_DATA_WARNING = 300


def parse_packet(datagram):
    """Return the reading in a "*!{json}" meter packet, or None for anything else.

    The Lightwave Link also broadcasts non-energy messages on this port, so
    only JSON objects carrying a current usage value are treated as readings.
    """
    if not datagram.startswith(b"*!"):
        return None
    try:
        body = json.loads(datagram[2:])
    except ValueError:
        return None
    if not isinstance(body, dict) or "cUse" not in body:
        return None
    return body


class LightwaveEnergyHub:
    """Shared UDP listener and cache for Lightwave energy data."""

    def __init__(self, scan_interval):
        """Initialize the shared hub."""
        self.scan_interval = scan_interval
        self.serial = ""
        self.mac = ""
        self.current_usage = None
        self.today_usage = None
        self.last_update = 0
        self.last_reading = time.time()
        self._quiet = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Never block Home Assistant's update thread waiting for a packet.
        self.sock.setblocking(False)
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
        """Use the newest queued meter reading if the scan interval has elapsed."""
        now = time.time()
        if self.sock is None or (now - self.last_update) < (self.scan_interval - 1):
            _LOGGER.debug("Lightwave energy update skipped; scan interval not elapsed")
            return
        self.last_update = now

        # The monitor broadcasts more often than we poll, so packets queue up in
        # the socket buffer. Drain the backlog and keep only the newest reading,
        # otherwise readings lag real time by however long the queue is.
        reading = None
        received = 0
        while True:
            try:
                datagram, _ = self.sock.recvfrom(1024)
            except BlockingIOError:
                break
            except OSError as err:
                _LOGGER.error("Failed reading LightwaveRF energy monitor data: %s", err)
                break
            received += 1
            parsed = parse_packet(datagram)
            if parsed is None:
                _LOGGER.debug("Ignoring non-meter Lightwave packet %s", datagram)
                continue
            reading = parsed

        if reading is None:
            self._check_quiet(now)
            return

        _LOGGER.debug("Lightwave energy reading %s (%s packets read)", reading, received)
        if self._quiet:
            _LOGGER.info("Lightwave energy monitor data resumed")
            self._quiet = False
        self.last_reading = now
        self.serial = reading.get("serial", "")
        self.mac = reading.get("mac", "")
        self.current_usage = reading.get("cUse")
        self.today_usage = reading.get("todUse")

    def _check_quiet(self, now):
        """Warn once when the monitor stops sending readings."""
        if self._quiet or (now - self.last_reading) < NO_DATA_WARNING:
            return
        self._quiet = True
        _LOGGER.warning(
            "No data from LightwaveRF energy monitor on UDP %s for over %s seconds",
            PORT,
            NO_DATA_WARNING,
        )

    def close(self, _event=None):
        """Close the UDP listener during shutdown."""
        if self.sock is None:
            return
        self.sock.close()
        self.sock = None


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Configure the sensor platform for home assistant."""
    scan_interval = hass.data[DATA_KEY]
    _LOGGER.debug("scan interval= %s", scan_interval)
    hub = LightwaveEnergyHub(scan_interval)
    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, hub.close)
    lightwave_devices = [
        LightwaveEnergy("CURRENT_USAGE", hub),
        LightwaveEnergy("TODAY_USAGE", hub),
    ]
    add_devices(lightwave_devices)


def _as_number(value):
    """Convert a packet value to a number, or None if it isn't one."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


class LightwaveEnergy(SensorEntity):
    """Primary class for Lightwave Energy."""

    def __init__(self, sensor_type, hub):
        """Initialize the sensor."""
        _LOGGER.debug("Lightwave Energy Init, sensor_type=%s", sensor_type)
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
    def device_class(self):
        """Return the Home Assistant device class."""
        if self.sensor_type == "CURRENT_USAGE":
            return SensorDeviceClass.POWER
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self):
        """Return the Home Assistant state class.

        Today's usage resets at midnight; total_increasing treats that drop as
        the start of a new cycle rather than negative consumption.
        """
        if self.sensor_type == "CURRENT_USAGE":
            return SensorStateClass.MEASUREMENT
        return SensorStateClass.TOTAL_INCREASING

    @property
    def native_unit_of_measurement(self):
        """UOM is either W or kWh."""
        if self.sensor_type == "CURRENT_USAGE":
            return UnitOfPower.WATT
        return UnitOfEnergy.KILO_WATT_HOUR

    @property
    def native_value(self):
        """Return the reading, or None (unknown) before the first packet."""
        if self.sensor_type == "CURRENT_USAGE":
            return _as_number(self.hub.current_usage)
        watt_hours = _as_number(self.hub.today_usage)
        if watt_hours is None:
            return None
        return watt_hours / 1000
