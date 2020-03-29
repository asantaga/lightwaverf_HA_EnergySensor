"""
Sensor Platform Device for LightwaveRF Electricity Monitor.

https://github.com/asantaga/wiserHomeAssistantPlatform
Angelo.santagata@gmail.com
"""

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import (
    CONF_HOST,
    CONF_MINIMUM,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
)
from homeassistant.helpers.discovery import load_platform

DOMAIN = "lightwaverf_energy"
DATA_KEY = "lightwaverf_energy"

PLATFORM_SCHEMA = vol.Schema(
    {vol.Optional(CONF_SCAN_INTERVAL, default=300): cv.positive_int}
)


def setup(hass, config):

    # Store the scan interval in the data storage.
    hass.data[DATA_KEY] = config[DOMAIN][0][CONF_SCAN_INTERVAL]
    print("scan interval***********************")
    print(config[DOMAIN][0][CONF_SCAN_INTERVAL])
    load_platform(hass, "sensor", DOMAIN, {}, config)
    return True
