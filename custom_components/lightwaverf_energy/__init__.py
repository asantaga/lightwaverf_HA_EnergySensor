"""
LightwaveRF Electricity Monitor integration for Home Assistant.

https://github.com/asantaga/lightwaverf_HA_EnergySensor
Angelo.santagata@gmail.com
"""

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers.discovery import load_platform

DOMAIN = "lightwaverf_energy"
DATA_KEY = "lightwaverf_energy"
DEFAULT_SCAN_INTERVAL = 30


def _single_entry(value):
    """Accept an empty key or a one-item list as well as a mapping."""
    if value is None:
        return {}
    if isinstance(value, list):
        return value[0] if value else {}
    return value


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            _single_entry,
            vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): cv.positive_int
                }
            ),
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, config):
    """Set up the Lightwave energy integration."""
    # Store the scan interval in the data storage.
    hass.data[DATA_KEY] = config[DOMAIN][CONF_SCAN_INTERVAL]
    load_platform(hass, "sensor", DOMAIN, {}, config)
    return True
