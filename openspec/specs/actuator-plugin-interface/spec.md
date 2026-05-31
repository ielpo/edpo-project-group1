# Actuator Plugin Interface

Version: v1

## ADDED Requirements

### Requirement: Minimal abstract interface on BaseActuator
`BaseActuator` SHALL declare exactly the following abstract methods:
- `apply(commands: list[dict]) -> None` — apply a batch of commands, mutating internal state
- `state() -> Any` — return a deep copy of the actuator's current state

`BaseActuator.__init__` SHALL accept `name: str` as its only required argument.

`to_dict()` and `reset()` SHALL NOT be part of the interface. Serialization is handled by FastAPI's `jsonable_encoder` on the value returned by `state()`. Reset is handled by the registry dispensing fresh instances (see ActuatorRegistry), not by a per-plugin method.

#### Scenario: Plugin implementing the abstract methods works end-to-end
- **WHEN** a plugin implements `apply()` and `state()`
- **THEN** the engine SHALL use the plugin without any duck-typing or fallback logic

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

Each command SHALL also update `last_command` to the command type string. Unknown command types SHALL be logged at WARNING level and skipped — they SHALL NOT raise.

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

### Requirement: ActuatorRegistry dispenses fresh actuator instances
`ActuatorRegistry` SHALL provide:
- `actuators() -> dict[str, BaseActuator]` — return a fresh dict of the known actuators (`left`, `right`), each a `DobotActuator` in default state

The registry mirrors `SensorRegistry.sensors()`: it is a dispenser of fresh working instances, not a live holder. It has no config file and no type inference. There SHALL be no on-demand creation of unknown actuators.

#### Scenario: actuators() returns the known dobots
- **WHEN** `registry.actuators()` is called
- **THEN** the result SHALL contain `DobotActuator` instances keyed `"left"` and `"right"`, each in default state

#### Scenario: actuators() returns fresh instances each call
- **WHEN** `registry.actuators()` is called twice
- **THEN** the two calls SHALL return distinct instances, so mutating one set SHALL NOT affect the other

### Requirement: Engine delegates to actuator working copy
The engine SHALL NOT contain inline command-application logic. The engine SHALL hold a working copy `self._actuators = self._actuator_registry.actuators()` (mirroring `self._sensors`) and call `self._actuators[robot_name].apply(command_list)` to apply commands and `self._actuators[robot_name].state()` to read dobot state. `engine.reset()` SHALL rebuild the working copy via `self._actuators = self._actuator_registry.actuators()`.

#### Scenario: Engine applies commands via actuator
- **WHEN** `handle_dobot_commands("left", [{"type": "move", "target": {"x": 1, "y": 2, "z": 3, "r": 0}}])` is called on the engine
- **THEN** the engine SHALL delegate to `self._actuators["left"].apply(...)`
- **AND** SHALL NOT contain a match/case block for command types

#### Scenario: Engine reads dobot state via actuator
- **WHEN** `get_dobot_state("left")` is called
- **THEN** the engine SHALL return `self._actuators["left"].state()`

#### Scenario: Unknown robot name is a hard failure
- **WHEN** `get_dobot_state("nonexistent")` is called
- **THEN** a `KeyError` SHALL propagate, which the API layer translates to HTTP 404
