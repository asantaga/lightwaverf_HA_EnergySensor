"""Tests for the Lightwave energy UDP hub and sensor metadata.

Home Assistant is stubbed out so these run with plain ``python -m unittest``.
"""
import importlib.util
import json
import pathlib
import socket
import sys
import threading
import types
import unittest
from types import SimpleNamespace

for name in ("homeassistant", "homeassistant.const", "homeassistant.helpers",
             "homeassistant.helpers.entity"):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules["homeassistant.const"].CONF_SCAN_INTERVAL = "scan_interval"
sys.modules["homeassistant.const"].EVENT_HOMEASSISTANT_STOP = "homeassistant_stop"
sys.modules["homeassistant.helpers.entity"].Entity = object

SENSOR_PATH = (pathlib.Path(__file__).resolve().parents[1]
               / "custom_components" / "lightwaverf_energy" / "sensor.py")
spec = importlib.util.spec_from_file_location("lightwaverf_energy_sensor", SENSOR_PATH)
sensor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sensor)


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

    def test_update_uses_newest_queued_packet(self):
        for c_use in (100, 200, 300, 400, 500):
            self.sender.sendto(packet(c_use, tod_use=c_use * 10), self.addr)

        self.hub.update()

        self.assertEqual(self.hub.current_usage, 500)
        self.assertEqual(self.hub.today_usage, 5000)
        self.hub.sock.setblocking(False)
        with self.assertRaises(BlockingIOError):
            self.hub.sock.recvfrom(1024)

    def test_update_restores_timeout(self):
        self.sender.sendto(packet(100), self.addr)
        self.hub.update()
        self.assertEqual(self.hub.sock.gettimeout(), 10.0)

    def test_update_waits_when_queue_empty(self):
        timer = threading.Timer(0.2, self.sender.sendto, (packet(750), self.addr))
        timer.start()
        try:
            self.hub.update()
        finally:
            timer.join()
        self.assertEqual(self.hub.current_usage, 750)


class LightwaveEnergyMetadataTest(unittest.TestCase):
    def test_today_usage_is_an_accumulating_energy_sensor(self):
        entity = sensor.LightwaveEnergy(
            "TODAY_USAGE", SimpleNamespace(today_usage="1250")
        )

        self.assertEqual(entity.device_class, "energy")
        self.assertEqual(entity.state_class, "total_increasing")
        self.assertEqual(entity.state, 1.25)
        self.assertEqual(entity.unique_id, "lightwaverf_energy_today_usage")

    def test_current_usage_is_an_instantaneous_power_sensor(self):
        entity = sensor.LightwaveEnergy(
            "CURRENT_USAGE", SimpleNamespace(current_usage="345")
        )

        self.assertEqual(entity.device_class, "power")
        self.assertEqual(entity.state_class, "measurement")
        self.assertEqual(entity.state, "345")
        self.assertEqual(entity.unique_id, "lightwaverf_energy_current_usage")

    def test_today_usage_is_empty_before_the_first_packet(self):
        entity = sensor.LightwaveEnergy(
            "TODAY_USAGE", SimpleNamespace(today_usage="")
        )

        self.assertEqual(entity.state, "")


if __name__ == "__main__":
    unittest.main()
