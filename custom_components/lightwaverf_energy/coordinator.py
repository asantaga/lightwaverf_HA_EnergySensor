"""Polling coordinator for the LightwaveRF Electricity Monitor."""
from datetime import timedelta
import logging

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import CONF_SERIAL, DEFAULT_SCAN_INTERVAL, DOMAIN, NO_DATA_TIMEOUT, PORT

_LOGGER = logging.getLogger(__name__)


def scan_interval(entry):
    """Return the configured polling interval for an entry."""
    return timedelta(seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))


def _as_number(value):
    """Convert a packet value to a number, or None if it isn't one."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


class LightwaveEnergyCoordinator(DataUpdateCoordinator):
    """Read the newest meter packet every scan interval."""

    def __init__(self, hass, entry, hub):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=scan_interval(entry),
        )
        self.hub = hub
        self._last_reading = dt_util.utcnow()

    async def _async_update_data(self):
        """Return the newest reading, keeping the last one between packets.

        Raising UpdateFailed marks the sensors unavailable, so a silent monitor
        doesn't leave its last reading looking live.
        """
        reading = await self.hass.async_add_executor_job(self.hub.read_latest)
        now = dt_util.utcnow()
        if reading is None:
            if now - self._last_reading >= timedelta(seconds=NO_DATA_TIMEOUT):
                raise UpdateFailed(
                    f"No data from LightwaveRF energy monitor on UDP {PORT} "
                    f"for over {NO_DATA_TIMEOUT} seconds"
                )
            return self.data or {}

        self._last_reading = now
        self._remember_serial(reading.get("serial"))
        today = _as_number(reading.get("todUse"))
        return {
            "current_usage": _as_number(reading.get("cUse")),
            "today_usage": None if today is None else today / 1000,
        }

    def _remember_serial(self, serial):
        """Store the monitor's serial so restarts stay locked to the same meter."""
        entry = self.config_entry
        if not serial or entry.data.get(CONF_SERIAL) == serial:
            return
        self.hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_SERIAL: serial}
        )
        dr.async_get(self.hass).async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entry.entry_id)},
            serial_number=serial,
        )
