"""Isolated unit tests for DobotActuator.

These exercise the command match/case directly on a DobotActuator instance —
no engine, no registry. This is the primary testing win from extracting the
actuator logic out of the engine.
"""

from simulated_factory.actuators.dobot import DobotActuator


def test_move_sets_absolute_position() -> None:
    actuator = DobotActuator("left")
    actuator.apply([{"type": "move", "target": {"x": 1, "y": 2, "z": 3, "r": 4}}])

    state = actuator.state()
    assert (state.position.x, state.position.y, state.position.z, state.position.r) == (
        1.0,
        2.0,
        3.0,
        4.0,
    )
    assert state.last_command == "move"


def test_move_keeps_unspecified_axes() -> None:
    actuator = DobotActuator("left")
    actuator.apply([{"type": "move", "target": {"x": 5}}])

    state = actuator.state()
    assert state.position.x == 5.0
    # Unspecified axes retain their prior (default) value.
    assert state.position.y == 0.0
    assert state.position.z == 0.0
    assert state.position.r == 0.0


def test_move_relative_offsets_current_position() -> None:
    actuator = DobotActuator("left")
    actuator.apply([{"type": "move", "target": {"x": 10, "y": 20, "z": 30, "r": 0}}])
    actuator.apply([{"type": "move-relative", "offset": {"x": 5, "z": -10}}])

    state = actuator.state()
    assert (state.position.x, state.position.y, state.position.z, state.position.r) == (
        15.0,
        20.0,
        20.0,
        0.0,
    )


def test_set_speed_with_acceleration() -> None:
    actuator = DobotActuator("left")
    actuator.apply([{"type": "set-speed", "speed": 80, "acceleration": 120}])

    state = actuator.state()
    assert state.speed == 80.0
    assert state.acceleration == 120.0


def test_set_speed_without_acceleration_keeps_default() -> None:
    actuator = DobotActuator("left")
    actuator.apply([{"type": "set-speed", "speed": 80}])

    state = actuator.state()
    assert state.speed == 80.0
    assert state.acceleration == 100.0  # unchanged default


def test_suction_cup_toggles() -> None:
    actuator = DobotActuator("left")
    actuator.apply([{"type": "suction-cup", "enabled": True}])
    assert actuator.state().suction_enabled is True

    actuator.apply([{"type": "suction-cup", "enabled": False}])
    assert actuator.state().suction_enabled is False


def test_run_conveyor_sets_speed_and_direction() -> None:
    actuator = DobotActuator("left")
    actuator.apply([{"type": "run-conveyor", "speed": 25, "direction": "FORWARD"}])

    state = actuator.state()
    assert state.conveyor_speed == 25.0
    assert state.conveyor_direction == "FORWARD"


def test_move_conveyor_sets_speed_distance_and_direction() -> None:
    actuator = DobotActuator("left")
    actuator.apply(
        [
            {
                "type": "move-conveyor",
                "speed": 30,
                "distance": 100,
                "direction": "BACKWARD",
            }
        ]
    )

    state = actuator.state()
    assert state.conveyor_speed == 30.0
    assert state.conveyor_distance == 100.0
    assert state.conveyor_direction == "BACKWARD"


def test_unknown_command_is_tolerated() -> None:
    actuator = DobotActuator("left")
    # Should not raise; last_command still records the type.
    actuator.apply([{"type": "unknown-future-type"}])
    assert actuator.state().last_command == "unknown-future-type"


def test_batch_applies_commands_in_order() -> None:
    actuator = DobotActuator("left")
    actuator.apply(
        [
            {"type": "move", "target": {"x": 1, "y": 1, "z": 1, "r": 0}},
            {"type": "move-relative", "offset": {"x": 2}},
            {"type": "suction-cup", "enabled": True},
        ]
    )

    state = actuator.state()
    assert state.position.x == 3.0
    assert state.suction_enabled is True
    assert state.last_command == "suction-cup"


def test_state_returns_deep_copy() -> None:
    actuator = DobotActuator("left")
    actuator.apply([{"type": "move", "target": {"x": 1, "y": 2, "z": 3, "r": 4}}])

    snapshot = actuator.state()
    snapshot.position.x = 999.0

    # Mutating the snapshot must not affect the actuator's internal state.
    assert actuator.state().position.x == 1.0
