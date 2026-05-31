## Why

`SimulationEngine` in `engine.py` contains ~50 lines and 7 methods (`_wire_sensors`, `_start_sensor_tasks`, `_stop_sensor_tasks`, `_pause_sensor_tasks`, `_resume_sensor_tasks`, `_apply_sensor_updates`, `_sensor_for`) that do nothing but iterate `self._sensors` and delegate to individual sensor plugin methods. These are pass-through orchestrations that belong in `SensorRegistry`, which already owns sensor creation. The engine's interface is shallower than it needs to be — callers must understand sensor lifecycle details that should be hidden behind the registry seam.

## What Changes

- Move sensor lifecycle management (wire, start, stop, pause, resume) into `SensorRegistry` as a unified `SensorPool`-style interface
- Move `_apply_sensor_updates` logic into `SensorRegistry` (it already has the `make()` method needed for lazy creation)
- Move `_sensor_for` (get-or-create by prefix) into `SensorRegistry`
- Reduce `SimulationEngine`'s sensor interaction to high-level calls: `start_all()`, `stop_all()`, `pause()`, `resume()`, `apply_updates(dict)`, `get_or_create(sensor_id)`
- Engine no longer imports or references `MqttSensor` directly

## Capabilities

### New Capabilities
- `sensor-pool-lifecycle`: SensorRegistry manages the full lifecycle of instantiated sensors (wiring, start/stop, pause/resume) behind a single interface

### Modified Capabilities
- `sensor-plugin-interface`: Sensor plugin interface gains lifecycle management through the registry rather than requiring callers to manage MQTT wiring directly

## Impact

- `services/simulated-factory/simulated_factory/sensor_registry.py` — gains lifecycle methods
- `services/simulated-factory/simulated_factory/engine.py` — loses 7 private methods, gains 5-6 delegation calls
- `services/simulated-factory/simulated_factory/sensors/base.py` — no changes (MqttSensor protocol unchanged)
- Existing tests that exercise engine sensor behaviour will need minor updates to account for the new delegation path
- No API changes — all external interfaces remain identical
