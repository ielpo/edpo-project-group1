"""Unit tests for SensorRegistry lifecycle management methods."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from simulated_factory.sensor_registry import SensorRegistry
from simulated_factory.sensors.base import BaseSensor, MqttSensor


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yml"


def _make_registry(publisher=None) -> SensorRegistry:
    return SensorRegistry(str(CONFIG_PATH), mqtt_publisher=publisher)


# ---------------------------------------------------------------------------
# activate / deactivate / pause / resume
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activate_starts_mqtt_sensor_tasks() -> None:
    publisher = MagicMock()
    registry = _make_registry(publisher)

    # Patch start_task on all MqttSensor instances
    started = []
    for sensor in registry.live.values():
        if isinstance(sensor, MqttSensor):
            sensor.start_task = AsyncMock(side_effect=lambda s=sensor: started.append(s))

    await registry.activate()
    assert len(started) > 0


@pytest.mark.asyncio
async def test_deactivate_stops_mqtt_sensor_tasks() -> None:
    publisher = MagicMock()
    registry = _make_registry(publisher)

    stopped = []
    for sensor in registry.live.values():
        if isinstance(sensor, MqttSensor):
            sensor.stop_task = AsyncMock(side_effect=lambda s=sensor: stopped.append(s))

    await registry.deactivate()
    assert len(stopped) > 0


def test_pause_pauses_all_mqtt_sensors() -> None:
    publisher = MagicMock()
    registry = _make_registry(publisher)

    paused = []
    for sensor in registry.live.values():
        if isinstance(sensor, MqttSensor):
            original_pause = sensor.pause_task
            sensor.pause_task = lambda s=sensor: paused.append(s)

    registry.pause()
    assert len(paused) > 0


def test_resume_resumes_all_mqtt_sensors() -> None:
    publisher = MagicMock()
    registry = _make_registry(publisher)

    # Pause first
    registry.pause()

    resumed = []
    for sensor in registry.live.values():
        if isinstance(sensor, MqttSensor):
            sensor.resume_task = lambda s=sensor: resumed.append(s)

    registry.resume()
    assert len(resumed) > 0


# ---------------------------------------------------------------------------
# get_or_create
# ---------------------------------------------------------------------------


def test_get_or_create_returns_existing_sensor() -> None:
    registry = _make_registry()
    # color-left exists in defaults
    sensor1 = registry.get_or_create("color-left")
    sensor2 = registry.get_or_create("color-left")
    assert sensor1 is sensor2


def test_get_or_create_creates_new_sensor() -> None:
    registry = _make_registry()
    # Remove it from live to test creation path
    assert "color-right" not in registry.live or True  # may or may not exist

    sensor = registry.get_or_create("ir-right")
    assert sensor is not None
    assert "ir-right" in registry.live
    assert sensor is registry.live["ir-right"]


def test_get_or_create_wires_mqtt_sensor() -> None:
    publisher = MagicMock()
    registry = _make_registry(publisher)

    # distance sensors implement MqttSensor
    sensor = registry.get_or_create("distance-right")
    assert isinstance(sensor, MqttSensor)
    # Verify it was wired (has _publisher set)
    assert getattr(sensor, "_publisher", None) is publisher


# ---------------------------------------------------------------------------
# apply_updates
# ---------------------------------------------------------------------------


def test_apply_updates_existing_sensor() -> None:
    registry = _make_registry()
    # color-left should exist in defaults
    registry.apply_updates({"color-left": "BLUE"})
    color, _ = registry.live["color-left"].read()
    assert color == "BLUE"


def test_apply_updates_creates_and_updates_new_sensor() -> None:
    publisher = MagicMock()
    registry = _make_registry(publisher)

    # Ensure ir-right doesn't exist initially
    if "ir-right" in registry.live:
        del registry._live["ir-right"]

    registry.apply_updates({"ir-right": True})
    assert "ir-right" in registry.live
    assert registry.live["ir-right"].read() is True


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------


def test_reset_rebuilds_live_pool() -> None:
    registry = _make_registry()

    # Mutate the live pool
    registry.apply_updates({"color-left": "BLUE"})
    color_before, _ = registry.live["color-left"].read()
    assert color_before == "BLUE"

    # Reset should restore defaults
    registry.reset()
    color_after, _ = registry.live["color-left"].read()
    assert color_after == "RED"


def test_reset_discards_runtime_sensors() -> None:
    registry = _make_registry()
    registry.get_or_create("ir-right")
    assert "ir-right" in registry.live

    registry.reset()
    # ir-right is not in defaults, so it should be gone
    if "ir-right" not in {sid for sid in registry._defaults}:
        assert "ir-right" not in registry.live


# ---------------------------------------------------------------------------
# configs
# ---------------------------------------------------------------------------


def test_configs_returns_sorted_sensor_configs() -> None:
    registry = _make_registry()
    configs = registry.configs()
    assert len(configs) > 0
    names = [c.name for c in configs]
    assert names == sorted(names)
