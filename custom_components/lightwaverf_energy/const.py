"""Constants for the LightwaveRF Electricity Monitor integration."""

DOMAIN = "lightwaverf_energy"
NAME = "Lightwave Energy Monitor"

PORT = 9761
CONF_SERIAL = "serial"
DEFAULT_SCAN_INTERVAL = 30
# Sensors become unavailable once the monitor has been silent this long (seconds).
NO_DATA_TIMEOUT = 300
