## 1. Create actuator plugin base

- [ ] 1.1 Create `actuators/__init__.py` with public imports
- [ ] 1.2 Create `actuators/base.py` with `BaseActuator` ABC (apply, state, to_dict, reset)

## 2. Implement DobotActuator

- [ ] 2.1 Create `actuators/dobot.py` with `DobotActuator` implementing `BaseActuator`
- [ ] 2.2 Move the match/case command logic from `engine.py` `_apply_dobot_commands` into `DobotActuator.apply()`

## 3. Create ActuatorRegistry

- [ ] 3.1 Create `actuator_registry.py` with `ActuatorRegistry` class (get, reset, all)

## 4. Refactor engine to use actuator registry

- [ ] 4.1 Add `ActuatorRegistry` to `SimulationEngine.__init__` replacing `self._dobots` dict
- [ ] 4.2 Replace `_apply_dobot_commands` call with `self._actuator_registry.get(robot_name).apply(command_list)`
- [ ] 4.3 Replace `get_dobot_state` to delegate to `self._actuator_registry.get(robot_name).state()`
- [ ] 4.4 Update `reset()` to call `self._actuator_registry.reset()`
- [ ] 4.5 Remove the now-unused `_apply_dobot_commands` method from engine

## 5. Tests

- [ ] 5.1 Add unit tests for `DobotActuator.apply()` covering all command types
- [ ] 5.2 Add unit test for `ActuatorRegistry` get/reset behavior
