"""Unit tests for ActuatorRegistry."""

from simulated_factory.actuator_registry import ActuatorRegistry
from simulated_factory.actuators.dobot import DobotActuator


def test_actuators_returns_known_dobots() -> None:
    registry = ActuatorRegistry()
    actuators = registry.actuators()

    assert set(actuators.keys()) == {"left", "right"}
    assert isinstance(actuators["left"], DobotActuator)
    assert isinstance(actuators["right"], DobotActuator)
    assert actuators["left"].name == "left"
    assert actuators["right"].name == "right"


def test_actuators_returns_default_state() -> None:
    registry = ActuatorRegistry()
    state = registry.actuators()["left"].state()

    assert state.position.x == 0.0
    assert state.speed == 50.0
    assert state.suction_enabled is False
    assert state.last_command is None


def test_actuators_returns_fresh_instances_each_call() -> None:
    registry = ActuatorRegistry()
    first = registry.actuators()
    second = registry.actuators()

    # Distinct instances: mutating one set must not affect the other.
    assert first["left"] is not second["left"]
    first["left"].apply([{"type": "move", "target": {"x": 42}}])

    assert first["left"].state().position.x == 42.0
    assert second["left"].state().position.x == 0.0
