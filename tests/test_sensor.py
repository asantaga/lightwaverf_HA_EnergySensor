"""Regression tests for LightwaveRF energy sensor metadata."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


homeassistant = types.ModuleType("homeassistant")
homeassistant_const = types.ModuleType("homeassistant.const")
homeassistant_const.CONF_SCAN_INTERVAL = "scan_interval"
homeassistant_const.EVENT_HOMEASSISTANT_STOP = "homeassistant_stop"
homeassistant_helpers = types.ModuleType("homeassistant.helpers")
homeassistant_entity = types.ModuleType("homeassistant.helpers.entity")
homeassistant_entity.Entity = type("Entity", (), {})

sys.modules.update(
    {
        "homeassistant": homeassistant,
        "homeassistant.const": homeassistant_const,
        "homeassistant.helpers": homeassistant_helpers,
        "homeassistant.helpers.entity": homeassistant_entity,
    }
)

spec = importlib.util.spec_from_file_location(
    "lightwaverf_energy_sensor",
    Path(__file__).parents[1] / "custom_components/lightwaverf_energy/sensor.py",
)
sensor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sensor_module)


class LightwaveEnergyMetadataTest(unittest.TestCase):
    def test_today_usage_is_an_accumulating_energy_sensor(self):
        sensor = sensor_module.LightwaveEnergy(
            "TODAY_USAGE", SimpleNamespace(today_usage="1250")
        )

        self.assertEqual(sensor.device_class, "energy")
        self.assertEqual(sensor.state_class, "total_increasing")
        self.assertEqual(sensor.state, 1.25)
        self.assertEqual(sensor.unique_id, "lightwaverf_energy_today_usage")

    def test_current_usage_is_an_instantaneous_power_sensor(self):
        sensor = sensor_module.LightwaveEnergy(
            "CURRENT_USAGE", SimpleNamespace(current_usage="345")
        )

        self.assertEqual(sensor.device_class, "power")
        self.assertEqual(sensor.state_class, "measurement")
        self.assertEqual(sensor.state, "345")
        self.assertEqual(sensor.unique_id, "lightwaverf_energy_current_usage")

    def test_today_usage_is_empty_before_the_first_packet(self):
        sensor = sensor_module.LightwaveEnergy(
            "TODAY_USAGE", SimpleNamespace(today_usage="")
        )

        self.assertEqual(sensor.state, "")
