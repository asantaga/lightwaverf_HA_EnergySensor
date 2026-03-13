"""
Sensor Platform Device for LightwaveRF Electricity Monitor.

https://github.com/asantaga/wiserHomeAssistantPlatform
Angelo.santagata@gmail.com
"""

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers.discovery import load_platform

DOMAIN = "lightwaverf_energy"
DATA_KEY = "lightwaverf_energy"

PLATFORM_SCHEMA = vol.Schema(
    {vol.Optional(CONF_SCAN_INTERVAL, default=300): cv.positive_int}
)


def setup(hass, config):
    """Set up the Lightwave energy integration."""
    domain_config = config.get(DOMAIN, {})
    if isinstance(domain_config, list):
        domain_config = domain_config[0] if domain_config else {}

    # Store the scan interval in the data storage.
    hass.data[DATA_KEY] = domain_config.get(CONF_SCAN_INTERVAL, 300)
    load_platform(hass, "sensor", DOMAIN, {}, config)
    return True
