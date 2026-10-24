"""
Sensor Platform Device for LightwaveRF Electricity Monitor.

https://github.com/asantaga/lightwaverf_HA_EnergySensor
Angelo.santagata@gmail.com
"""
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CONF_SCAN_INTERVAL, UnitOfEnergy, UnitOfPower
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import async_import_yaml
from .const import CONF_SERIAL, DEFAULT_SCAN_INTERVAL, DOMAIN, NAME

_LOGGER = logging.getLogger(__name__)

# Unique IDs and entity IDs are kept from earlier versions so history and
# statistics carry over.
OBJECT_IDS = {
    "current_usage": "electricity_current_usage_w",
    "today_usage": "electricity_energy_today_usage_kwh",
}

SENSORS = (
    SensorEntityDescription(
        key="current_usage",
        name="Current usage",
        icon="mdi:flash",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    # Today's usage resets at midnight; total_increasing treats that drop as
    # the start of a new cycle rather than negative consumption.
    SensorEntityDescription(
        key="today_usage",
        name="Today's usage",
        icon="mdi:flash",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Import the old `sensor: - platform: lightwaverf_energy` YAML."""
    _LOGGER.warning(
        "Configuring %s under sensor: is no longer supported; it has been imported "
        "into the UI. Remove it from configuration.yaml",
        DOMAIN,
    )
    interval = config.get(CONF_SCAN_INTERVAL)
    seconds = (
        int(interval.total_seconds()) if hasattr(interval, "total_seconds")
        else interval or DEFAULT_SCAN_INTERVAL
    )
    await async_import_yaml(hass, {CONF_SCAN_INTERVAL: seconds})


async def async_setup_entry(hass, entry, async_add_entities):
    """Add the two monitor sensors."""
    coordinator = entry.runtime_data
    async_add_entities(LightwaveEnergy(coordinator, description) for description in SENSORS)


class LightwaveEnergy(CoordinatorEntity, SensorEntity):
    """A reading from the Lightwave energy monitor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, description):
        """Initialize the sensor."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        # Suggest the pre-2.0 entity ID; otherwise new installs would get one
        # built from the device and sensor names.
        self.entity_id = f"sensor.{OBJECT_IDS[description.key]}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="LightwaveRF",
            model="Electricity monitor",
            serial_number=entry.data.get(CONF_SERIAL),
        )

    @property
    def native_value(self):
        """Return the reading, or None (unknown) before the first packet."""
        return self.coordinator.data.get(self.entity_description.key)
