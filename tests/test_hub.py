"""Tests for the UDP listener."""
import time

import pytest

from custom_components.lightwaverf_energy.hub import LightwaveEnergyHub, parse_packet

from .conftest import packet, send


@pytest.fixture
def hub():
    hub = LightwaveEnergyHub()
    yield hub
    hub.close()


def test_returns_newest_queued_reading(hub):
    send(hub, *(packet(c, tod_use=c * 10) for c in (100, 200, 300, 400, 500)))

    reading = hub.read_latest()

    assert reading["cUse"] == 500
    assert reading["todUse"] == 5000
    with pytest.raises(BlockingIOError):
        hub.sock.recvfrom(1024)


def test_returns_none_without_blocking_when_queue_empty(hub):
    started = time.monotonic()
    assert hub.read_latest() is None
    assert time.monotonic() - started < 1.0


def test_ignores_packets_that_are_not_meter_readings(hub):
    send(
        hub,
        packet(100, tod_use=1100),
        b"*!not json",
        b"garbage",
        b'*!{"trans": 2, "fn": "on", "room": 1}',
        b"*![1, 2, 3]",
    )

    assert hub.read_latest()["cUse"] == 100


@pytest.mark.parametrize(
    "datagram",
    [b"", b"*!", b"*!{}", b"*!null", b'{"cUse": 1}', b"*!\xff\xfe"],
)
def test_parse_packet_rejects_non_readings(datagram):
    assert parse_packet(datagram) is None


def test_locks_on_to_first_monitor(hub, caplog):
    send(hub, packet(100, serial="FIRST"), packet(200, serial="OTHER"))
    assert hub.read_latest()["cUse"] == 100
    assert hub.serial == "FIRST"
    assert "Ignoring Lightwave energy monitor OTHER" in caplog.text

    send(hub, packet(300, serial="OTHER"), packet(400, serial="FIRST"))
    assert hub.read_latest()["cUse"] == 400
    assert caplog.text.count("Ignoring Lightwave energy monitor OTHER") == 1


def test_known_serial_is_used_from_the_start():
    hub = LightwaveEnergyHub(serial="KNOWN")
    try:
        send(hub, packet(100, serial="OTHER"))
        assert hub.read_latest() is None
    finally:
        hub.close()


def test_close_is_idempotent(hub):
    hub.close()
    hub.close()
    assert hub.read_latest() is None
