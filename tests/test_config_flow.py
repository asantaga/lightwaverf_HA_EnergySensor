"""Tests for UI set-up and YAML import."""
from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lightwaverf_energy.const import DOMAIN, NAME


async def test_user_flow_creates_entry(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == "form"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 45}
    )
    await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert result["title"] == NAME
    assert result["options"] == {CONF_SCAN_INTERVAL: 45}


async def test_only_one_entry_allowed(hass):
    MockConfigEntry(domain=DOMAIN, data={}, options={CONF_SCAN_INTERVAL: 30}).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result["type"] == "abort"
    assert result["reason"] == "single_instance_allowed"


async def test_user_flow_reports_port_in_use(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    with patch(
        "custom_components.lightwaverf_energy.config_flow.LightwaveEnergyHub",
        side_effect=OSError("Address already in use"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: 30}
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "cannot_bind"}


async def test_user_flow_rejects_zero_interval(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    schema = result["data_schema"]
    try:
        schema({CONF_SCAN_INTERVAL: 0})
    except Exception:  # noqa: BLE001 - voluptuous raises Invalid subclasses
        return
    raise AssertionError("scan_interval of 0 was accepted")


async def test_yaml_is_imported_with_repair_issue(hass, issue_registry: ir.IssueRegistry):
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: {CONF_SCAN_INTERVAL: 60}})
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].options == {CONF_SCAN_INTERVAL: 60}
    assert issue_registry.async_get_issue(HOMEASSISTANT_DOMAIN, f"deprecated_yaml_{DOMAIN}")


async def test_empty_yaml_key_is_imported_with_default(hass):
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: None})
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert entries[0].options == {CONF_SCAN_INTERVAL: 30}


async def test_yaml_import_does_not_duplicate_entry(hass):
    MockConfigEntry(domain=DOMAIN, data={}, options={CONF_SCAN_INTERVAL: 30}).add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {DOMAIN: {CONF_SCAN_INTERVAL: 60}})
    await hass.async_block_till_done()

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_old_sensor_platform_yaml_is_imported(hass, issue_registry: ir.IssueRegistry):
    assert await async_setup_component(
        hass, "sensor", {"sensor": [{"platform": DOMAIN, CONF_SCAN_INTERVAL: 45}]}
    )
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].options == {CONF_SCAN_INTERVAL: 45}
    assert issue_registry.async_get_issue(HOMEASSISTANT_DOMAIN, f"deprecated_yaml_{DOMAIN}")
