"""Unit tests for built-in sensor plugins."""

import pytest

from simulated_factory.models import SensorUpdateRequest
from simulated_factory.sensors.color import ColorSensor
from simulated_factory.sensors.distance import DistanceSensor
from simulated_factory.sensors.ir import IrSensor


# ---------------------------------------------------------------------------
# ColorSensor
# ---------------------------------------------------------------------------


def test_color_sensor_reads_current_value() -> None:
    sensor = ColorSensor(
        "color-left", {"value": "RED", "raw_color": [255, 0, 0]}
    )
    color, raw = sensor.read()
    assert color == "RED"
    assert raw == [255, 0, 0]


def test_color_sensor_default_fallback() -> None:
    sensor = ColorSensor("color-left", {"value": None})
    color, raw = sensor.read()
    assert color == "YELLOW"


def test_color_sensor_update() -> None:
    sensor = ColorSensor("color-left", {"value": "RED"})
    sensor.update("BLUE")
    assert sensor.read()[0] == "BLUE"


def test_color_sensor_to_dict() -> None:
    sensor = ColorSensor("color-left", {"value": "RED"})
    d = sensor.to_dict()
    assert d["sensorId"] == "color-left"
    assert d["value"] == "RED"
    assert "mode" not in d
    assert "scripted_values" not in d


def test_color_sensor_apply_update() -> None:
    sensor = ColorSensor("color-left", {"value": "RED"})
    sensor.apply_update({"value": "GREEN", "raw_color": [0, 255, 0]})
    assert sensor._cfg.value == "GREEN"
    assert sensor._cfg.raw_color == [0, 255, 0]


def test_color_sensor_clone_is_independent() -> None:
    sensor = ColorSensor("color-left", {"value": "RED"})
    cloned = sensor.clone()
    cloned.update("BLUE")
    assert sensor.read()[0] == "RED"
    assert cloned.read()[0] == "BLUE"


# ---------------------------------------------------------------------------
# IrSensor
# ---------------------------------------------------------------------------


def test_ir_sensor_true() -> None:
    sensor = IrSensor("ir-left", {"value": True})
    assert sensor.read() is True


def test_ir_sensor_false() -> None:
    sensor = IrSensor("ir-left", {"value": False})
    assert sensor.read() is False


def test_ir_sensor_default_true_when_none() -> None:
    sensor = IrSensor("ir-left", {"value": None})
    assert sensor.read() is True


def test_ir_sensor_update() -> None:
    sensor = IrSensor("ir-left", {"value": True})
    sensor.update(False)
    assert sensor.read() is False


def test_ir_sensor_to_dict() -> None:
    sensor = IrSensor("ir-left", {"value": True})
    d = sensor.to_dict()
    assert d["sensorId"] == "ir-left"
    assert d["value"] is True
    assert "mode" not in d
    assert "scripted_values" not in d


# ---------------------------------------------------------------------------
# DistanceSensor
# ---------------------------------------------------------------------------


def test_distance_sensor_reads_current_value() -> None:
    sensor = DistanceSensor("distance-conveyor", {"value": 30.0})
    assert sensor.read() == 30.0


def test_distance_sensor_default_fallback() -> None:
    sensor = DistanceSensor("distance-conveyor", {"value": None})
    assert sensor.read() == 30.0


def test_distance_sensor_update() -> None:
    sensor = DistanceSensor("distance-conveyor", {"value": 30.0})
    sensor.update(15.0)
    assert sensor.read() == 15.0


def test_distance_sensor_to_config_has_metadata() -> None:
    sensor = DistanceSensor(
        "distance-conveyor",
        {
            "value": 30.0,
            "mqtt_topic": "sensors/distance/Conveyor/distance_IR_short_left",
            "uid": "TFu",
            "location": "Conveyor",
            "message_type": "distance_IR_short_left",
            "cadence_ms": 250,
        },
    )
    cfg = sensor.to_config()
    assert cfg.sensorId == "distance-conveyor"
    assert cfg.uid == "TFu"
    assert cfg.location == "Conveyor"
    assert cfg.cadence_ms == 250


def test_distance_sensor_mqtt_message_uses_current_value() -> None:
    sensor = DistanceSensor(
        "distance-conveyor",
        {
            "value": 30.0,
            "mqtt_topic": "sensors/distance/topic",
            "uid": "TFu",
            "location": "Conveyor",
        },
    )

    message = sensor.mqtt_message()
    assert message is not None
    topic, payload = message
    assert topic == "sensors/distance/topic"
    assert '"distance": 30.0' in payload


def test_distance_sensor_mqtt_message_returns_none_when_value_missing() -> None:
    sensor = DistanceSensor(
        "distance-conveyor",
        {
            "value": None,
            "mqtt_topic": "sensors/distance/topic",
        },
    )
    assert sensor.mqtt_message() is None


def test_distance_sensor_clone_is_independent() -> None:
    sensor = DistanceSensor("distance-conveyor", {"mode": "fixed", "value": 30.0})
    cloned = sensor.clone()
    cloned.update(10.0)
    assert sensor.read() == 30.0
    assert cloned.read() == 10.0


# ---------------------------------------------------------------------------
# apply_update
# ---------------------------------------------------------------------------


def test_apply_update_updates_value_and_raw_color() -> None:
    sensor = ColorSensor(
        "color-left", {"mode": "fixed", "value": "RED", "raw_color": [255, 0, 0]}
    )
    sensor.apply_update({"value": "BLUE", "raw_color": [0, 0, 255]})
    color, raw = sensor.read()
    assert color == "BLUE"
    assert raw == [0, 0, 255]


def test_apply_update_ignores_type_key() -> None:
    sensor = ColorSensor("color-left", {"mode": "fixed", "value": "RED"})
    # type key must not cause an AttributeError on SensorConfig
    sensor.apply_update({"type": "color", "value": "GREEN"})
    assert sensor.read()[0] == "GREEN"
