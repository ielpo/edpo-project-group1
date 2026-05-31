## Why

The dobot command handling logic (`_apply_dobot_commands`, `_apply_dobot_commands` match/case block, `DobotRuntimeState` tracking) lives inline in `engine.py`, making the engine large and mixing orchestration concerns with actuator-specific logic. Sensors already have a clean plugin architecture (`sensors/base.py`, `SensorRegistry`). Extracting actuator logic into an equivalent `actuators/` subfolder with a plugin interface keeps the engine focused on orchestration and makes actuator behavior testable and extensible independently.

## What Changes

- Extract dobot command application logic from `engine.py` into a new `actuators/` subfolder
- Introduce a `BaseActuator` abstract class mirroring `BaseSensor` (apply commands, read state, serialize)
- Create a `DobotActuator` plugin implementing the interface for the existing dobot command types
- Create an `ActuatorRegistry` that instantiates and manages actuator plugins (mirroring `SensorRegistry`)
- Refactor `engine.py` to delegate command application to the actuator registry instead of inline logic

## Capabilities

### New Capabilities
- `actuator-plugin-interface`: Defines the abstract contract for actuator plugins — apply commands, read state, serialize. Mirrors the sensor plugin interface.

### Modified Capabilities

## Impact

- `services/simulated-factory/simulated_factory/engine.py` — removes `_apply_dobot_commands` and direct `DobotRuntimeState` manipulation; delegates to actuator registry
- New directory `services/simulated-factory/simulated_factory/actuators/` with `base.py`, `dobot.py`, `__init__.py`
- New file `services/simulated-factory/simulated_factory/actuator_registry.py`
- `models.py` — `DobotRuntimeState` and `Position` remain as data models, used by the dobot actuator plugin
- Existing tests for dobot command handling will need updating to target the new actuator plugin
