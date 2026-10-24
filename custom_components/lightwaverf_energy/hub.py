"""UDP listener for the LightwaveRF Electricity Monitor."""
import json
import logging
import socket

from . import const

_LOGGER = logging.getLogger(__name__)


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
    """Non-blocking UDP listener that returns the newest meter reading."""

    def __init__(self, port=None, serial=None):
        """Bind the listener; serial locks it to one monitor if already known."""
        self.serial = serial
        self._ignored_serials = set()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Never block Home Assistant waiting for a packet.
        self.sock.setblocking(False)
        for opt_name in ("SO_REUSEADDR", "SO_REUSEPORT"):
            opt = getattr(socket, opt_name, None)
            if opt is not None:
                try:
                    self.sock.setsockopt(socket.SOL_SOCKET, opt, 1)
                except OSError as err:
                    _LOGGER.debug("Unable to set %s on UDP socket: %s", opt_name, err)
        try:
            self.sock.bind(("0.0.0.0", const.PORT if port is None else port))
        except OSError:
            self.sock.close()
            self.sock = None
            raise

    def read_latest(self):
        """Drain the socket and return the newest reading, or None if there was none.

        The monitor broadcasts more often than we poll, so packets queue up in
        the socket buffer. Keeping only the newest stops readings lagging real
        time by however long the queue is.
        """
        reading = None
        received = 0
        while self.sock is not None:
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
            if not self._accepts(parsed.get("serial")):
                continue
            reading = parsed
        if reading is not None:
            _LOGGER.debug("Lightwave energy reading %s (%s packets read)", reading, received)
        return reading

    def _accepts(self, serial):
        """Lock on to the first monitor seen and ignore any others."""
        if not serial:
            return True
        if self.serial is None:
            self.serial = serial
            return True
        if serial == self.serial:
            return True
        if serial not in self._ignored_serials:
            self._ignored_serials.add(serial)
            _LOGGER.info(
                "Ignoring Lightwave energy monitor %s; using monitor %s",
                serial,
                self.serial,
            )
        return False

    def close(self, *_):
        """Close the UDP listener."""
        if self.sock is None:
            return
        self.sock.close()
        self.sock = None
