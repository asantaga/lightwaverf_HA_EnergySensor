"""
LightwaveRF Electricity Monitor integration for Home Assistant.

https://github.com/asantaga/lightwaverf_HA_EnergySensor
Angelo.santagata@gmail.com
"""
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir

from .const import CONF_SERIAL, DEFAULT_SCAN_INTERVAL, DOMAIN, NAME, PORT
from .coordinator import LightwaveEnergyCoordinator, scan_interval
from .hub import LightwaveEnergyHub

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


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


async def async_setup(hass, config):
    """Import YAML configuration into a config entry."""
    if DOMAIN in config:
        hass.async_create_task(async_import_yaml(hass, config[DOMAIN]))
    return True


async def async_import_yaml(hass, import_data):
    """Create (or keep) the config entry for YAML users and flag the YAML for removal."""
    await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=import_data
    )
    ir.async_create_issue(
        hass,
        HOMEASSISTANT_DOMAIN,
        f"deprecated_yaml_{DOMAIN}",
        is_fixable=False,
        issue_domain=DOMAIN,
        severity=ir.IssueSeverity.WARNING,
        translation_key="deprecated_yaml",
        translation_placeholders={"domain": DOMAIN, "integration_title": NAME},
    )


async def async_setup_entry(hass, entry):
    """Start listening for the monitor and set up its sensors."""
    try:
        hub = await hass.async_add_executor_job(
            lambda: LightwaveEnergyHub(serial=entry.data.get(CONF_SERIAL))
        )
    except OSError as err:
        raise ConfigEntryNotReady(f"Unable to listen on UDP port {PORT}: {err}") from err
    entry.async_on_unload(hub.close)

    coordinator = LightwaveEnergyCoordinator(hass, entry, hub)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass, entry):
    """Apply a new polling interval without reloading (saving the serial lands here too)."""
    entry.runtime_data.update_interval = scan_interval(entry)


async def async_unload_entry(hass, entry):
    """Unload the sensors; the listener is closed by async_on_unload."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
