"""Unit tests for SensorRegistry construction and preset-specific sensor maps."""

from pathlib import Path

import pytest

from simulated_factory.sensor_registry import SensorRegistry


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yml"


def _make_registry() -> SensorRegistry:
    return SensorRegistry(str(CONFIG_PATH))


def test_registry_loads_default_sensors() -> None:
    registry = _make_registry()
    sensors = registry.sensors()

    assert "color-left" in sensors
    assert "ir-left" in sensors
    assert "distance-left" in sensors


def test_registry_live_pool_clones_defaults() -> None:
    registry = _make_registry()
    defaults = registry.sensors()
    live = registry.live

    default_color, _ = defaults["color-left"].read()
    live_color, _ = live["color-left"].read()
    assert default_color == "RED"
    assert live_color == "RED"

    live["color-left"].update("GREEN")
    untouched_default, _ = defaults["color-left"].read()
    mutated_live, _ = live["color-left"].read()
    assert untouched_default == "RED"
    assert mutated_live == "GREEN"


def test_registry_make_known_type() -> None:
    registry = _make_registry()
    sensor = registry.make("color-sample", {"type": "color", "value": "RED"})

    assert sensor.__class__.__name__ == "ColorSensor"
    assert sensor.to_dict()["type"] == "color"


def test_registry_make_unknown_prefix_falls_back_to_generic() -> None:
    registry = _make_registry()
    sensor = registry.make("mystery-sensor", {})

    assert sensor.__class__.__name__ == "GenericSensor"
    sensor.update("VALUE")
    assert sensor.read() == "VALUE"


def test_registry_make_unknown_explicit_type_raises_runtime_error() -> None:
    registry = _make_registry()
    with pytest.raises(RuntimeError):
        registry.make("bad-sensor", {"type": "does-not-exist"})
