## 1. Create actuator plugin base

- [x] 1.1 Create `actuators/__init__.py` with public imports
- [x] 1.2 Create `actuators/base.py` with `BaseActuator` ABC (apply, state only)

## 2. Implement DobotActuator

- [x] 2.1 Create `actuators/dobot.py` with `DobotActuator` implementing `BaseActuator`
- [x] 2.2 Move the match/case command logic from `engine.py` `_apply_dobot_commands` into `DobotActuator.apply()` (unknown commands logged at WARNING)

## 3. Create ActuatorRegistry

- [x] 3.1 Create `actuator_registry.py` with `ActuatorRegistry.actuators()` returning a fresh `{left, right}` dict

## 4. Refactor engine to use actuator registry

- [x] 4.1 Add `ActuatorRegistry` to `SimulationEngine.__init__` and set `self._actuators = registry.actuators()`, replacing the `self._dobots` dict
- [x] 4.2 Replace `_apply_dobot_commands` calls with `self._actuators[robot_name].apply(command_list)`
- [x] 4.3 Replace `get_dobot_state` and `get_status` to read via `self._actuators[robot_name].state()`; API catches `KeyError` → HTTP 404
- [x] 4.4 Update `reset()` to rebuild `self._actuators = self._actuator_registry.actuators()`
- [x] 4.5 Remove the now-unused `_apply_dobot_commands` method and unused imports from engine

## 5. Tests

- [x] 5.1 Add unit tests for `DobotActuator.apply()` covering all command types (and unknown-command tolerance)
- [x] 5.2 Add unit test for `ActuatorRegistry.actuators()` returning fresh default instances
- [x] 5.3 Update engine tests that read `engine._dobots` to use `engine.get_dobot_state()`
