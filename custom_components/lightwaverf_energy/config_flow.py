"""Config flow for the LightwaveRF Electricity Monitor."""
import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, NAME
from .hub import LightwaveEnergyHub

_LOGGER = logging.getLogger(__name__)


def _interval_schema(default):
    return vol.Schema(
        {
            vol.Optional(CONF_SCAN_INTERVAL, default=default): vol.All(
                vol.Coerce(int), vol.Range(min=1)
            )
        }
    )


def _check_port():
    """Raise OSError if the UDP listener can't be bound."""
    LightwaveEnergyHub().close()


class LightwaveEnergyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up the monitor listener from the UI or from YAML."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Ask for the polling interval and check the UDP port can be used."""
        errors = {}
        if user_input is not None:
            try:
                await self.hass.async_add_executor_job(_check_port)
            except OSError as err:
                _LOGGER.error("Unable to listen for the Lightwave energy monitor: %s", err)
                errors["base"] = "cannot_bind"
            else:
                return self.async_create_entry(title=NAME, data={}, options=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_interval_schema(DEFAULT_SCAN_INTERVAL),
            errors=errors,
        )

    async def async_step_import(self, import_data):
        """Create an entry from YAML configuration."""
        return self.async_create_entry(
            title=NAME,
            data={},
            options={
                CONF_SCAN_INTERVAL: import_data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return LightwaveEnergyOptionsFlow()


class LightwaveEnergyOptionsFlow(OptionsFlow):
    """Change the polling interval."""

    async def async_step_init(self, user_input=None):
        """Show or save the polling interval."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(step_id="init", data_schema=_interval_schema(current))
