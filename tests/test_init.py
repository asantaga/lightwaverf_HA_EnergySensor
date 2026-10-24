"""Tests for setting up the integration and its sensors."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_SCAN_INTERVAL, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lightwaverf_energy.const import (
    CONF_SERIAL,
    DOMAIN,
    NAME,
    NO_DATA_TIMEOUT,
)

from .conftest import packet, send

CURRENT = "sensor.electricity_current_usage_w"
TODAY = "sensor.electricity_energy_today_usage_kwh"


@pytest.fixture
def entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, title=NAME, data={}, options={CONF_SCAN_INTERVAL: 30}
    )
    entry.add_to_hass(hass)
    return entry


async def setup(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry.runtime_data


async def refresh(hass, coordinator):
    await coordinator.async_refresh()
    await hass.async_block_till_done()


async def test_sensors_start_unknown_then_show_newest_reading(hass, entry):
    coordinator = await setup(hass, entry)
    assert hass.states.get(CURRENT).state == STATE_UNKNOWN
    assert hass.states.get(TODAY).state == STATE_UNKNOWN

    send(coordinator.hub, packet(410, tod_use=7100), packet(523, tod_use=7250))
    await refresh(hass, coordinator)

    current = hass.states.get(CURRENT)
    assert current.state == "523"
    assert current.attributes["device_class"] == "power"
    assert current.attributes["state_class"] == "measurement"
    assert current.attributes["unit_of_measurement"] == "W"
    assert current.attributes["friendly_name"] == "Lightwave Energy Monitor Current usage"

    today = hass.states.get(TODAY)
    assert today.state == "7.25"
    assert today.attributes["device_class"] == "energy"
    assert today.attributes["state_class"] == "total_increasing"
    assert today.attributes["unit_of_measurement"] == "kWh"
    assert today.attributes["friendly_name"] == "Lightwave Energy Monitor Today's usage"


async def test_unique_ids_are_unchanged(hass, entry, entity_registry: er.EntityRegistry):
    await setup(hass, entry)
    assert entity_registry.async_get(CURRENT).unique_id == "lightwaverf_energy_current_usage"
    assert entity_registry.async_get(TODAY).unique_id == "lightwaverf_energy_today_usage"


async def test_existing_yaml_entities_keep_their_ids(hass, entry, entity_registry: er.EntityRegistry):
    """Entities registered by the old YAML set-up move to the config entry."""
    old = entity_registry.async_get_or_create(
        "sensor", DOMAIN, "lightwaverf_energy_current_usage",
        suggested_object_id="electricity_current_usage_w",
    )
    assert old.config_entry_id is None

    await setup(hass, entry)

    migrated = entity_registry.async_get(CURRENT)
    assert migrated.id == old.id
    assert migrated.config_entry_id == entry.entry_id


async def test_sensors_go_unavailable_when_monitor_is_silent(hass, entry, freezer):
    coordinator = await setup(hass, entry)
    send(coordinator.hub, packet(523))
    await refresh(hass, coordinator)
    assert hass.states.get(CURRENT).state == "523"

    freezer.tick(timedelta(seconds=NO_DATA_TIMEOUT - 30))
    await refresh(hass, coordinator)
    assert hass.states.get(CURRENT).state == "523"

    freezer.tick(timedelta(seconds=60))
    await refresh(hass, coordinator)
    assert hass.states.get(CURRENT).state == STATE_UNAVAILABLE
    assert hass.states.get(TODAY).state == STATE_UNAVAILABLE

    send(coordinator.hub, packet(600))
    await refresh(hass, coordinator)
    assert hass.states.get(CURRENT).state == "600"


async def test_polls_at_configured_interval(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={CONF_SCAN_INTERVAL: 90})
    entry.add_to_hass(hass)
    coordinator = await setup(hass, entry)
    assert coordinator.update_interval == timedelta(seconds=90)


async def test_options_change_interval_without_reload(hass, entry):
    coordinator = await setup(hass, entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 10}
    )
    await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert entry.options[CONF_SCAN_INTERVAL] == 10
    assert entry.runtime_data is coordinator
    assert coordinator.update_interval == timedelta(seconds=10)


async def test_device_records_monitor_serial(hass, entry, device_registry: dr.DeviceRegistry, entity_registry: er.EntityRegistry):
    coordinator = await setup(hass, entry)
    [device] = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    assert device.manufacturer == "LightwaveRF"
    assert entity_registry.async_get(CURRENT).device_id == device.id
    assert entity_registry.async_get(TODAY).device_id == device.id

    send(coordinator.hub, packet(523, serial="ABC123"))
    await refresh(hass, coordinator)

    assert entry.data[CONF_SERIAL] == "ABC123"
    assert device_registry.async_get(device.id).serial_number == "ABC123"
    assert entry.runtime_data is coordinator  # saving the serial doesn't reload


async def test_stays_on_saved_monitor_after_restart(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_SERIAL: "MINE"}, options={CONF_SCAN_INTERVAL: 30}
    )
    entry.add_to_hass(hass)
    coordinator = await setup(hass, entry)

    send(coordinator.hub, packet(999, serial="NEIGHBOUR"), packet(250, serial="MINE"))
    await refresh(hass, coordinator)

    assert hass.states.get(CURRENT).state == "250"


async def test_retries_when_port_unavailable(hass, entry):
    with patch(
        "custom_components.lightwaverf_energy.LightwaveEnergyHub",
        side_effect=OSError("Address already in use"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_closes_listener(hass, entry):
    coordinator = await setup(hass, entry)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert coordinator.hub.sock is None
