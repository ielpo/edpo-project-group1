## Context

`SimulationEngine` (engine.py, ~400 lines) currently owns the full sensor lifecycle: wiring MQTT publishers, starting/stopping background tasks, pausing/resuming during interactive gating, applying step-based sensor updates, and lazy sensor creation by prefix. Meanwhile, `SensorRegistry` only handles creation and preset parsing — it hands off raw sensor instances and never touches them again.

The engine iterates `self._sensors.values()` in 7 private methods, checking `isinstance(sensor, MqttSensor)` each time. This knowledge about which sensors need MQTT wiring is an implementation detail that leaks through the engine's interface.

## Goals / Non-Goals

**Goals:**
- Move sensor lifecycle management (wire, start, stop, pause, resume) into `SensorRegistry`
- Move `_apply_sensor_updates` and `_sensor_for` (get-or-create) into `SensorRegistry`
- Engine interacts with sensors through 5-6 high-level methods on the registry
- Engine no longer imports or type-checks `MqttSensor`
- Sensor lifecycle is testable in isolation (without engine)

**Non-Goals:**
- Changing the sensor plugin interface (`BaseSensor`, `MqttSensor` ABCs remain unchanged)
- Splitting engine.py into the full 4-subcomponent architecture from ARCHITECTURE.md (that's separate work)
- Modifying any API endpoints or external behaviour
- Changing preset YAML format or sensor config structure

## Decisions

### 1. Extend SensorRegistry with a "live pool" role

**Decision**: Add lifecycle methods directly to `SensorRegistry` rather than creating a separate `SensorPool` class.

**Rationale**: The registry already holds `_defaults` and `make()`. Adding a `_live: dict[str, BaseSensor]` field and lifecycle methods keeps the sensor domain in one module. A separate class would just delegate to the registry for creation anyway — it'd be shallow.

**Alternative considered**: Separate `SensorPool` class wrapping the registry. Rejected because it adds a seam with only one adapter and no independent testability gain.

### 2. Registry receives the MQTT publisher at construction

**Decision**: Pass the `mqtt_publisher` to `SensorRegistry.__init__()` so it can wire sensors automatically on creation.

**Rationale**: Eliminates the two-phase "create then wire" pattern. Every sensor that implements `MqttSensor` gets wired immediately when the registry instantiates it.

**Alternative considered**: Pass publisher to each lifecycle method. Rejected — it spreads a single dependency across every call instead of injecting once.

### 3. Lifecycle methods on the registry

New public methods on `SensorRegistry`:

```python
def activate(self) -> None           # wire + start all MQTT sensors
async def deactivate(self) -> None   # stop all MQTT sensors
def pause(self) -> None              # pause all MQTT sensors
def resume(self) -> None             # resume all MQTT sensors
def apply_updates(self, updates: dict[str, Any]) -> None  # apply step sensor updates
def get_or_create(self, sensor_id: str) -> BaseSensor     # lazy get-or-create
def reset(self) -> None              # rebuild live pool from defaults
def configs(self) -> list[SensorConfig]                   # list all configs
```

### 4. Engine delegates, doesn't orchestrate

**Decision**: Engine calls `self._sensor_registry.activate()` etc. — one line per lifecycle transition instead of a for-loop with isinstance checks.

**Rationale**: The engine's job is coordinating the simulation run (presets, state transitions, interactive gating). Sensor details are an implementation leak.

## Risks / Trade-offs

- **[Coupling registry to MQTT publisher]** → Acceptable: the publisher is already injected into `build_dependencies()` and passed to engine. Moving it one level closer to where it's used reduces indirection.
- **[Larger SensorRegistry responsibility]** → Mitigated: the class stays under ~150 lines. Creation + lifecycle is a natural single responsibility ("manage sensors").
- **[Test migration]** → Low risk: existing engine tests that mock sensors will need minor adjustments to mock at the registry level instead. The change simplifies rather than complicates test setup.
