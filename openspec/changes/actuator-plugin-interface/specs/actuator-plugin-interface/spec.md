# Actuator Plugin Interface

Version: v1

## ADDED Requirements

### Requirement: Complete abstract interface on BaseActuator
`BaseActuator` SHALL declare the following abstract methods:
- `apply(commands: list[dict]) -> None` — apply a batch of commands, mutating internal state
- `state() -> Any` — return a deep copy of the actuator's current state
- `to_dict() -> dict[str, Any]` — serialize the actuator state for API responses
- `reset() -> None` — restore the actuator to its initial state

`BaseActuator.__init__` SHALL accept `name: str` as its only required argument.

#### Scenario: Plugin implementing all abstract methods works end-to-end
- **WHEN** a plugin implements `apply()`, `state()`, `to_dict()`, and `reset()`
- **THEN** the engine SHALL use the plugin via the registry without any duck-typing or fallback logic

#### Scenario: state() returns a deep copy
- **WHEN** `state()` is called on an actuator
- **THEN** mutations to the returned object SHALL NOT affect the actuator's internal state

### Requirement: DobotActuator implements BaseActuator
`DobotActuator` SHALL implement `BaseActuator` and handle the following command types:
- `move` — set absolute position from `target` field
- `move-relative` — offset current position from `offset` field
- `set-speed` — set speed (and optionally acceleration)
- `suction-cup` — set suction enabled/disabled
- `run-conveyor` — set conveyor speed and direction
- `move-conveyor` — set conveyor speed, distance, and direction

Each command SHALL also update `last_command` to the command type string. Unknown command types SHALL be silently ignored (logged at info level).

#### Scenario: move command sets absolute position
- **WHEN** `apply([{"type": "move", "target": {"x": 1, "y": 2, "z": 3, "r": 4}}])` is called
- **THEN** the actuator's position SHALL be `Position(x=1, y=2, z=3, r=4)`
- **AND** `last_command` SHALL be `"move"`

#### Scenario: move-relative offsets current position
- **WHEN** the actuator is at position `(10, 20, 30, 0)` and `apply([{"type": "move-relative", "offset": {"x": 5, "z": -10}}])` is called
- **THEN** the position SHALL be `(15, 20, 20, 0)`

#### Scenario: Unknown command type is ignored
- **WHEN** `apply([{"type": "unknown-future-type"}])` is called
- **THEN** no error SHALL be raised
- **AND** `last_command` SHALL be `"unknown-future-type"`

### Requirement: ActuatorRegistry manages actuator instances
`ActuatorRegistry` SHALL provide:
- `get(name: str) -> BaseActuator` — return the actuator for the given name, creating a default `DobotActuator` if not present
- `reset() -> None` — reset all managed actuators to initial state
- `all() -> dict[str, BaseActuator]` — return all actuator instances

#### Scenario: Getting an actuator by name
- **WHEN** `registry.get("left")` is called
- **THEN** a `DobotActuator` named `"left"` SHALL be returned

#### Scenario: Getting the same name twice returns the same instance
- **WHEN** `registry.get("left")` is called twice
- **THEN** the same actuator instance SHALL be returned both times

#### Scenario: Reset clears all actuator state
- **WHEN** commands have been applied to actuators and `registry.reset()` is called
- **THEN** all actuators SHALL return to their initial default state

### Requirement: Engine delegates to ActuatorRegistry
The engine SHALL NOT contain inline command-application logic. The engine SHALL call `self._actuator_registry.get(robot_name).apply(command_list)` to apply commands and `self._actuator_registry.get(robot_name).state()` to read dobot state.

#### Scenario: Engine applies commands via actuator
- **WHEN** `handle_dobot_commands("left", [{"type": "move", "target": {"x": 1, "y": 2, "z": 3, "r": 0}}])` is called on the engine
- **THEN** the engine SHALL delegate to `actuator_registry.get("left").apply(...)` 
- **AND** SHALL NOT contain a match/case block for command types

#### Scenario: Engine reads dobot state via actuator
- **WHEN** `get_dobot_state("left")` is called
- **THEN** the engine SHALL return `actuator_registry.get("left").state()`
