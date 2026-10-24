"""Shared fixtures for the Lightwave energy tests."""
import json
import socket
import time

import pytest

from custom_components.lightwaverf_energy import const

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load the integration from custom_components."""
    yield


@pytest.fixture(autouse=True)
def lightwave_port(socket_enabled, monkeypatch):
    """Listen on an ephemeral port rather than 9761 so a live install isn't disturbed."""
    monkeypatch.setattr(const, "PORT", 0)


def packet(c_use, tod_use=1000, serial="ABC123"):
    """Build a datagram in the monitor's "*!{json}" format."""
    body = {"trans": 1, "mac": "20:3B:85", "time": 0, "prod": "pwrMtr",
            "serial": serial, "signal": 0, "type": "energy",
            "cUse": c_use, "maxUse": 900, "todUse": tod_use, "yesUse": 9000}
    return b"*!" + json.dumps(body).encode()


def send(hub, *datagrams):
    """Send datagrams to a hub's socket over loopback."""
    port = hub.sock.getsockname()[1]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        for datagram in datagrams:
            sender.sendto(datagram, ("127.0.0.1", port))
    # Loopback delivery is effectively instant, but give the kernel a moment.
    time.sleep(0.05)
