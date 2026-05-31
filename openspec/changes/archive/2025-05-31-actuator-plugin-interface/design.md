## Context

The simulated-factory service uses a plugin architecture for sensors (`sensors/base.py`, `SensorRegistry`). Sensor plugins implement `BaseSensor` (read, update, to_dict, clone) and are discovered/instantiated via a registry. The engine delegates all sensor logic to these plugins.

Dobot command handling, however, is implemented inline in `engine.py` via `_apply_dobot_commands` — a large match/case block that mutates `DobotRuntimeState` directly. This makes the engine responsible for actuator-specific logic, complicating testing and extension.

## Goals / Non-Goals

**Goals:**
- Mirror the sensor plugin architecture for actuators (`actuators/` subfolder, `BaseActuator`, `ActuatorRegistry`)
- Extract the existing dobot command logic into a `DobotActuator` plugin
- Keep the engine focused on orchestration — it calls `actuator.apply(commands)` and `actuator.state()`
- Keep the interface minimal — only what's needed for the current dobot use case
- Breaking API changes are acceptable where they produce a simpler or more correct implementation; dependents will be fixed separately

**Non-Goals:**
- MQTT publishing for actuators (sensors handle that; actuators respond to commands)
- Config-file-driven actuator discovery (hardcode dobot actuators for now; registry is just a holder)
- Multiple actuator types beyond dobot (only add the extension point, don't build other actuators)
- Fixing dependents broken by API changes (tracked separately)

## Decisions

### 1. BaseActuator interface

`BaseActuator` will be an ABC with two methods:
- `apply(commands: list[dict]) -> None` — apply a batch of commands to internal state
- `state() -> Any` — return a deep copy of the current state; mirrors `BaseSensor.read() -> Any`; engine casts to `DobotRuntimeState` at dobot-specific boundaries (same pattern as `read_color`/`read_ir`)

`to_dict()` and `reset()` are excluded:
- `to_dict()` dropped — no call site in the engine or API layer; `DobotRuntimeState` is serialized directly by FastAPI via `jsonable_encoder`
- `reset()` dropped — reset follows the sensor pattern: registry dispenses fresh instances via `actuators()`, engine replaces `self._actuators` wholesale (same as `self._sensors = self._sensor_registry.sensors()`)

**Rationale**: Minimal surface area. `apply` replaces the inline match/case. `state() -> Any` keeps the interface type-agnostic for future actuator types while allowing typed access at concrete boundaries.

**Alternative considered**: Single `handle_command(cmd)` method per command — rejected because the engine already batches commands and splitting them adds no value.

### 2. ActuatorRegistry is a simple holder, not a dynamic loader

Unlike `SensorRegistry` which does importlib-based discovery from config, `ActuatorRegistry` will instantiate the known dobot actuators (`left`, `right`) directly via an `actuators()` method that returns fresh instances — mirroring `SensorRegistry.sensors()` which returns fresh clones. No config file, no type inference rules.

**Rationale**: There's only one actuator type. Over-engineering the registry adds complexity without benefit. The extension point exists via `BaseActuator` — new types can be added later with dynamic loading if needed. Fresh-instance pattern avoids in-place mutation and eliminates reference-aliasing risk on reset.

### 3. DobotActuator owns Position and DobotRuntimeState mutation

The existing `_apply_dobot_commands` match/case moves into `DobotActuator.apply()`. The plugin owns a `DobotRuntimeState` instance internally.

Unknown command types are logged at `WARNING` level and skipped — not raised. The dobot command set can be extended at the hardware level; the simulator tolerates unrecognised commands. The current `logger.info` call is upgraded to `logger.warning`.

**Rationale**: Direct 1:1 extraction with one deliberate behavioral change: unknown commands escalate from INFO to WARNING to make integration issues visible without crashing the service.

### 4. Engine delegates via registry

The engine holds an `ActuatorRegistry` (constructed in `__init__`) and a working copy `self._actuators = self._actuator_registry.actuators()`, mirroring `self._sensors`. `handle_dobot_commands` calls `self._actuators[robot_name].apply(command_list)` instead of `self._apply_dobot_commands(robot_name, command_list)`. `get_dobot_state` returns `self._actuators[robot_name].state()`.

Dict access (`self._actuators[robot_name]`) raises `KeyError` for unknown names. The current `setdefault` auto-create behavior (`engine.py:493` and `engine.py:625`) is removed — a caller passing an unrecognised robot name gets a hard failure, not a silently spawned phantom actuator. The API layer catches `KeyError` from both the command and state endpoints and returns HTTP 404.

On-demand creation is considered an error for both actuators and sensors. The sensor on-demand creation in `_sensor_for()` and `_apply_sensor_updates()` is out of scope here but is similarly wrong.

### 5. Test coverage

`DobotActuator` gets a dedicated `tests/test_dobot_actuator.py` that exercises each command type directly on a `DobotActuator` instance — no engine, no registry. This is the primary testing win from the refactor: the match/case logic becomes independently testable.

Engine-level tests (`test_engine.py`) are updated to assert via `engine.get_dobot_state("left").position.x` instead of `engine._dobots["left"].position.x`. Engine tests verify delegation happens; they do not re-test every command branch.

## Risks / Trade-offs

- [Minimal risk] Adding a layer of indirection for only one actuator type — mitigated by keeping the registry trivial (no dynamic loading, no config parsing)
- [Low risk] Engine tests that access `engine._dobots` directly will need updating — replaced with `engine.get_dobot_state()` calls, which are already public API
