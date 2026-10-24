"""Checks on the manifest, HACS metadata and translations."""
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
COMPONENT = REPO / "custom_components" / "lightwaverf_energy"


def test_manifest():
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert list(manifest)[:2] == ["domain", "name"]
    assert list(manifest)[2:] == sorted(list(manifest)[2:])
    assert manifest["documentation"] == "https://github.com/asantaga/lightwaverf_HA_EnergySensor"
    assert manifest["issue_tracker"].endswith("/issues")
    assert manifest["iot_class"] == "local_polling"
    assert manifest["config_flow"] is True
    assert manifest["single_config_entry"] is True
    assert manifest["integration_type"] == "device"
    assert manifest["version"]


def test_hacs_metadata():
    hacs = json.loads((REPO / "hacs.json").read_text())
    assert hacs["name"]
    assert hacs["homeassistant"] == "2024.12.0"


def test_translations_cover_flows():
    strings = json.loads((COMPONENT / "translations" / "en.json").read_text())
    assert "scan_interval" in strings["config"]["step"]["user"]["data"]
    assert "cannot_bind" in strings["config"]["error"]
    assert "scan_interval" in strings["options"]["step"]["init"]["data"]
