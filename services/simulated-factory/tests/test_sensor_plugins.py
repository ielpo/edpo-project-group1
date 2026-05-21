"""Unit tests for built-in sensor plugins."""
from __future__ import annotations

import pytest

from simulated_factory.models import SensorUpdateRequest
from simulated_factory.sensors.color import ColorSensor
from simulated_factory.sensors.distance import DistanceSensor
from simulated_factory.sensors.ir import IrSensor


# ---------------------------------------------------------------------------
# ColorSensor
# ---------------------------------------------------------------------------


def test_color_sensor_fixed_mode() -> None:
    sensor = ColorSensor("color-left", {"mode": "fixed", "value": "RED", "raw_color": [1, 0, 0]})
    color, raw = sensor.read()
    assert color == "RED"
    assert raw == [1, 0, 0]


def test_color_sensor_default_fallback() -> None:
    sensor = ColorSensor("color-left", {"mode": "fixed", "value": None})
    color, raw = sensor.read()
    assert color == "YELLOW"


def test_color_sensor_scripted_mode() -> None:
    sensor = ColorSensor(
        "color-left",
        {"mode": "scripted", "scripted_values": ["BLUE", "GREEN", "YELLOW"]},
    )
    assert sensor.read(step=1)[0] == "BLUE"
    assert sensor.read(step=2)[0] == "GREEN"
    assert sensor.read(step=3)[0] == "YELLOW"
    # Out-of-range clamps to last
    assert sensor.read(step=99)[0] == "YELLOW"


def test_color_sensor_scripted_step_zero_uses_first() -> None:
    sensor = ColorSensor(
        "color-left",
        {"mode": "scripted", "scripted_values": ["RED", "BLUE"]},
    )
    assert sensor.read(step=0)[0] == "RED"


def test_color_sensor_update() -> None:
    sensor = ColorSensor("color-left", {"mode": "fixed", "value": "RED"})
    sensor.update("BLUE")
    assert sensor.read()[0] == "BLUE"


def test_color_sensor_to_dict() -> None:
    sensor = ColorSensor("color-left", {"mode": "fixed", "value": "RED"})
    d = sensor.to_dict()
    assert d["sensorId"] == "color-left"
    assert d["mode"] == "fixed"
    assert d["value"] == "RED"


def test_color_sensor_apply_update_request() -> None:
    sensor = ColorSensor("color-left", {"mode": "fixed", "value": "RED"})
    sensor.apply_update_request({"value": "GREEN", "raw_color": [0, 1, 0]})
    assert sensor._cfg.value == "GREEN"
    assert sensor._cfg.raw_color == [0, 1, 0]


def test_color_sensor_clone_is_independent() -> None:
    sensor = ColorSensor("color-left", {"mode": "fixed", "value": "RED"})
    cloned = sensor.clone()
    cloned.update("BLUE")
    assert sensor.read()[0] == "RED"
    assert cloned.read()[0] == "BLUE"


# ---------------------------------------------------------------------------
# IrSensor
# ---------------------------------------------------------------------------


def test_ir_sensor_fixed_true() -> None:
    sensor = IrSensor("ir-left", {"mode": "fixed", "value": True})
    assert sensor.read() is True


def test_ir_sensor_fixed_false() -> None:
    sensor = IrSensor("ir-left", {"mode": "fixed", "value": False})
    assert sensor.read() is False


def test_ir_sensor_default_true_when_none() -> None:
    sensor = IrSensor("ir-left", {"mode": "fixed", "value": None})
    assert sensor.read() is True


def test_ir_sensor_scripted_mode() -> None:
    sensor = IrSensor("ir-left", {"mode": "scripted", "scripted_values": [True, False, True]})
    assert sensor.read(step=1) is True
    assert sensor.read(step=2) is False
    assert sensor.read(step=3) is True


def test_ir_sensor_update() -> None:
    sensor = IrSensor("ir-left", {"mode": "fixed", "value": True})
    sensor.update(False)
    assert sensor.read() is False


def test_ir_sensor_to_dict() -> None:
    sensor = IrSensor("ir-left", {"mode": "fixed", "value": True})
    d = sensor.to_dict()
    assert d["sensorId"] == "ir-left"
    assert d["value"] is True


# ---------------------------------------------------------------------------
# DistanceSensor
# ---------------------------------------------------------------------------


def test_distance_sensor_fixed_mode() -> None:
    sensor = DistanceSensor("distance-conveyor", {"mode": "fixed", "value": 30.0})
    assert sensor.read() == 30.0


def test_distance_sensor_default_fallback() -> None:
    sensor = DistanceSensor("distance-conveyor", {"mode": "fixed", "value": None})
    assert sensor.read() == 30.0


def test_distance_sensor_scripted_mode() -> None:
    sensor = DistanceSensor(
        "distance-conveyor",
        {"mode": "scripted", "scripted_values": [30.0, 12.5, 6.2, 30.0]},
    )
    assert sensor.read(step=1) == 30.0
    assert sensor.read(step=2) == 12.5
    assert sensor.read(step=3) == 6.2
    assert sensor.read(step=4) == 30.0
    # clamps to last
    assert sensor.read(step=99) == 30.0


def test_distance_sensor_update() -> None:
    sensor = DistanceSensor("distance-conveyor", {"mode": "fixed", "value": 30.0})
    sensor.update(15.0)
    assert sensor.read() == 15.0


def test_distance_sensor_to_sensor_config_has_metadata() -> None:
    sensor = DistanceSensor(
        "distance-conveyor",
        {
            "mode": "scripted",
            "value": 30.0,
            "mqtt_topic": "sensors/distance/Conveyor/distance_IR_short_left",
            "uid": "TFu",
            "location": "Conveyor",
            "message_type": "distance_IR_short_left",
            "cadence_ms": 250,
        },
    )
    cfg = sensor.to_sensor_config()
    assert cfg.sensorId == "distance-conveyor"
    assert cfg.uid == "TFu"
    assert cfg.location == "Conveyor"
    assert cfg.cadence_ms == 250


def test_distance_sensor_clone_is_independent() -> None:
    sensor = DistanceSensor("distance-conveyor", {"mode": "fixed", "value": 30.0})
    cloned = sensor.clone()
    cloned.update(10.0)
    assert sensor.read() == 30.0
    assert cloned.read() == 10.0


# ---------------------------------------------------------------------------
# apply_overrides
# ---------------------------------------------------------------------------


def test_apply_overrides_updates_value_and_raw_color() -> None:
    sensor = ColorSensor("color-left", {"mode": "fixed", "value": "RED", "raw_color": [1, 0, 0]})
    sensor.apply_overrides({"value": "BLUE", "raw_color": [0, 0, 1]})
    color, raw = sensor.read()
    assert color == "BLUE"
    assert raw == [0, 0, 1]


def test_apply_overrides_ignores_type_key() -> None:
    sensor = ColorSensor("color-left", {"mode": "fixed", "value": "RED"})
    # type key must not cause an AttributeError on SensorConfig
    sensor.apply_overrides({"type": "color", "value": "GREEN"})
    assert sensor.read()[0] == "GREEN"
