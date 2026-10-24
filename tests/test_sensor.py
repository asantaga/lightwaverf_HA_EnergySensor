"""Tests for the Lightwave energy integration.

Home Assistant is stubbed out so these run with plain ``python -m unittest``.
The stubs are only installed while the integration modules are imported, so
they don't leak into other test modules. The config schema tests need
``voluptuous`` and are skipped when it isn't installed.
"""
import importlib.util
import json
import logging
import pathlib
import socket
import sys
import time
import types
import unittest
from enum import StrEnum
from types import SimpleNamespace
from unittest import mock

try:
    import voluptuous as vol
except ImportError:  # pragma: no cover - depends on the local environment
    vol = None

REPO = pathlib.Path(__file__).resolve().parents[1]
COMPONENT = REPO / "custom_components" / "lightwaverf_energy"


def _stub_modules():
    """Build minimal stand-ins for the Home Assistant modules we import."""
    const = types.ModuleType("homeassistant.const")
    const.CONF_SCAN_INTERVAL = "scan_interval"
    const.EVENT_HOMEASSISTANT_STOP = "homeassistant_stop"
    const.UnitOfPower = StrEnum("UnitOfPower", {"WATT": "W"})
    const.UnitOfEnergy = StrEnum("UnitOfEnergy", {"KILO_WATT_HOUR": "kWh"})

    sensor_component = types.ModuleType("homeassistant.components.sensor")
    sensor_component.SensorEntity = type("SensorEntity", (), {})
    sensor_component.SensorDeviceClass = StrEnum(
        "SensorDeviceClass", {"POWER": "power", "ENERGY": "energy"}
    )
    sensor_component.SensorStateClass = StrEnum(
        "SensorStateClass",
        {"MEASUREMENT": "measurement", "TOTAL_INCREASING": "total_increasing"},
    )

    config_validation = types.ModuleType("homeassistant.helpers.config_validation")
    config_validation.positive_int = (
        mock.Mock() if vol is None else vol.All(vol.Coerce(int), vol.Range(min=0))
    )

    discovery = types.ModuleType("homeassistant.helpers.discovery")
    discovery.load_platform = mock.Mock()

    modules = {
        "homeassistant": types.ModuleType("homeassistant"),
        "homeassistant.const": const,
        "homeassistant.components": types.ModuleType("homeassistant.components"),
        "homeassistant.components.sensor": sensor_component,
        "homeassistant.helpers": types.ModuleType("homeassistant.helpers"),
        "homeassistant.helpers.config_validation": config_validation,
        "homeassistant.helpers.discovery": discovery,
    }
    if vol is None:
        modules["voluptuous"] = mock.MagicMock()
    return modules


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STUBS = _stub_modules()
with mock.patch.dict(sys.modules, STUBS):
    sensor = _load("lightwaverf_energy_sensor", COMPONENT / "sensor.py")
    integration = _load("lightwaverf_energy_init", COMPONENT / "__init__.py")


def packet(c_use, tod_use=1000):
    """Build a datagram in the monitor's "*!{json}" format."""
    body = {"trans": 1, "mac": "20:3B:85", "time": 0, "prod": "pwrMtr",
            "serial": "ABC123", "signal": 0, "type": "energy",
            "cUse": c_use, "todUse": tod_use}
    return b"*!" + json.dumps(body).encode()


class LightwaveEnergyHubTest(unittest.TestCase):
    def setUp(self):
        # Bind an ephemeral port rather than 9761 so a live install isn't disturbed.
        self._port = sensor.PORT
        sensor.PORT = 0
        self.hub = sensor.LightwaveEnergyHub(scan_interval=30)
        self.addr = ("127.0.0.1", self.hub.sock.getsockname()[1])
        self.sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def tearDown(self):
        self.sender.close()
        self.hub.close()
        sensor.PORT = self._port

    def send(self, *datagrams):
        for datagram in datagrams:
            self.sender.sendto(datagram, self.addr)
        # Loopback delivery is effectively instant, but give the kernel a moment.
        time.sleep(0.05)

    def test_update_uses_newest_queued_packet(self):
        self.send(*(packet(c, tod_use=c * 10) for c in (100, 200, 300, 400, 500)))

        self.hub.update()

        self.assertEqual(self.hub.current_usage, 500)
        self.assertEqual(self.hub.today_usage, 5000)
        with self.assertRaises(BlockingIOError):
            self.hub.sock.recvfrom(1024)

    def test_update_does_not_block_when_queue_empty(self):
        started = time.monotonic()
        self.hub.update()
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertIsNone(self.hub.current_usage)
        self.assertIsNone(self.hub.today_usage)

    def test_update_keeps_previous_reading_when_queue_empty(self):
        self.send(packet(640, tod_use=3200))
        self.hub.update()

        self.hub.last_update = 0  # let the next poll through the throttle
        self.hub.update()

        self.assertEqual(self.hub.current_usage, 640)
        self.assertEqual(self.hub.today_usage, 3200)

    def test_update_ignores_packets_that_are_not_meter_readings(self):
        self.send(
            packet(100, tod_use=1100),
            b"*!not json",
            b"garbage",
            b'*!{"trans": 2, "fn": "on", "room": 1}',
            b"*![1, 2, 3]",
        )

        self.hub.update()

        self.assertEqual(self.hub.current_usage, 100)
        self.assertEqual(self.hub.today_usage, 1100)
        self.assertEqual(self.hub.serial, "ABC123")

    def test_update_respects_scan_interval(self):
        self.send(packet(100))
        self.hub.update()
        self.send(packet(200))

        self.hub.update()  # within the scan interval, so nothing is read

        self.assertEqual(self.hub.current_usage, 100)

    def test_warns_once_when_monitor_goes_quiet(self):
        now = [1_000_000.0]
        with mock.patch.object(sensor.time, "time", side_effect=lambda: now[0]):
            self.send(packet(100))
            self.hub.update()

            with self.assertLogs(sensor._LOGGER, logging.WARNING) as logs:
                for _ in range(3):
                    now[0] += sensor.NO_DATA_WARNING + 1
                    self.hub.update()
            self.assertEqual(len(logs.records), 1)

            self.send(packet(300))
            now[0] += 60
            with self.assertLogs(sensor._LOGGER, logging.INFO) as logs:
                self.hub.update()
            self.assertIn("resumed", logs.output[0])
            self.assertEqual(self.hub.current_usage, 300)


class LightwaveEnergyEntityTest(unittest.TestCase):
    def test_is_a_sensor_entity(self):
        self.assertTrue(
            issubclass(sensor.LightwaveEnergy, STUBS["homeassistant.components.sensor"].SensorEntity)
        )
        # SensorEntity.state is final; values must come through native_value.
        self.assertNotIn("state", vars(sensor.LightwaveEnergy))
        self.assertNotIn("unit_of_measurement", vars(sensor.LightwaveEnergy))

    def test_today_usage_is_an_accumulating_energy_sensor(self):
        entity = sensor.LightwaveEnergy(
            "TODAY_USAGE", SimpleNamespace(today_usage=1250)
        )

        self.assertEqual(entity.device_class, "energy")
        self.assertEqual(entity.state_class, "total_increasing")
        self.assertEqual(entity.native_unit_of_measurement, "kWh")
        self.assertEqual(entity.native_value, 1.25)
        self.assertEqual(entity.unique_id, "lightwaverf_energy_today_usage")
        self.assertEqual(entity.name, "Electricity Energy Today Usage (kWh)")

    def test_current_usage_is_an_instantaneous_power_sensor(self):
        entity = sensor.LightwaveEnergy(
            "CURRENT_USAGE", SimpleNamespace(current_usage="345")
        )

        self.assertEqual(entity.device_class, "power")
        self.assertEqual(entity.state_class, "measurement")
        self.assertEqual(entity.native_unit_of_measurement, "W")
        self.assertEqual(entity.native_value, 345)
        self.assertEqual(entity.unique_id, "lightwaverf_energy_current_usage")
        self.assertEqual(entity.name, "Electricity Current Usage (W)")

    def test_values_are_unknown_before_the_first_packet(self):
        hub = SimpleNamespace(current_usage=None, today_usage=None)

        self.assertIsNone(sensor.LightwaveEnergy("CURRENT_USAGE", hub).native_value)
        self.assertIsNone(sensor.LightwaveEnergy("TODAY_USAGE", hub).native_value)

    def test_non_numeric_values_are_unknown(self):
        hub = SimpleNamespace(current_usage="n/a", today_usage="")

        self.assertIsNone(sensor.LightwaveEnergy("CURRENT_USAGE", hub).native_value)
        self.assertIsNone(sensor.LightwaveEnergy("TODAY_USAGE", hub).native_value)


@unittest.skipIf(vol is None, "voluptuous not installed")
class ConfigSchemaTest(unittest.TestCase):
    def interval(self, domain_config):
        config = integration.CONFIG_SCHEMA({integration.DOMAIN: domain_config})
        return config[integration.DOMAIN]["scan_interval"]

    def test_default_scan_interval_is_30_seconds(self):
        self.assertEqual(self.interval({}), 30)
        self.assertEqual(self.interval(None), 30)

    def test_scan_interval_is_read(self):
        self.assertEqual(self.interval({"scan_interval": 60}), 60)
        self.assertEqual(self.interval([{"scan_interval": 45}]), 45)

    def test_invalid_scan_interval_is_rejected(self):
        with self.assertRaises(vol.Invalid):
            self.interval({"scan_interval": "soon"})

    def test_other_integrations_are_left_alone(self):
        config = integration.CONFIG_SCHEMA(
            {integration.DOMAIN: {}, "sensor": [{"platform": "template"}]}
        )
        self.assertIn("sensor", config)

    def test_setup_stores_interval_and_loads_sensor_platform(self):
        hass = SimpleNamespace(data={})
        config = integration.CONFIG_SCHEMA({integration.DOMAIN: {"scan_interval": 90}})
        with mock.patch.object(integration, "load_platform") as load_platform:
            self.assertTrue(integration.setup(hass, config))
        self.assertEqual(hass.data[integration.DATA_KEY], 90)
        load_platform.assert_called_once()


class PackagingTest(unittest.TestCase):
    def test_manifest(self):
        manifest = json.loads((COMPONENT / "manifest.json").read_text())
        self.assertEqual(list(manifest)[:2], ["domain", "name"])
        self.assertEqual(
            manifest["documentation"],
            "https://github.com/asantaga/lightwaverf_HA_EnergySensor",
        )
        self.assertEqual(manifest["iot_class"], "local_polling")
        self.assertIn("issue_tracker", manifest)
        self.assertIn("version", manifest)

    def test_hacs_metadata(self):
        hacs = json.loads((REPO / "hacs.json").read_text())
        self.assertIn("name", hacs)
        self.assertIn("homeassistant", hacs)


if __name__ == "__main__":
    unittest.main()
