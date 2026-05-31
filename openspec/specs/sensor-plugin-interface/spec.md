# Sensor Plugin Interface

Version: v1

## Purpose

Define the complete, mandatory contract for sensor plugins. Every method a plugin must implement is declared here. The engine and sensor registry SHALL interact with sensors only through this interface — no duck-typing, no attribute probing, no fallback chains.

## Requirements

### Requirement: Complete abstract interface on BaseSensor
`BaseSensor` SHALL declare the following methods:

Abstract (must be overridden by every plugin):
- `read(step: int = 0) -> Any`
- `update(value: Any) -> None`
- `to_dict() -> dict[str, Any]`

With default implementations (may be overridden):
- `clone() -> BaseSensor` — deep-copy config, construct same class
- `to_config() -> SensorConfig` — return deep copy of `self._cfg`
- `apply_update(data: dict[str, Any]) -> None` — strip `type`, set matching fields on `self._cfg`

`BaseSensor` SHALL NOT implement `__getattr__`. Code outside a plugin SHALL access sensor state only through `read()`, `to_config()`, and `to_dict()`.

#### Scenario: Plugin implementing only abstract methods works end-to-end
- **WHEN** a plugin implements `read()`, `update()`, and `to_dict()`
- **THEN** the default `clone()`, `to_config()`, and `apply_update()` SHALL be used
- **AND** the sensor SHALL behave correctly in the engine without any duck-typing fallback

#### Scenario: Plugin overrides clone for custom deep-copy logic
- **WHEN** a plugin defines its own `clone()` method
- **THEN** the engine SHALL call the plugin's `clone()` and SHALL NOT fall back to any copy or try-except logic

### Requirement: to_dict() is owned entirely by each plugin
Each plugin SHALL implement `to_dict()` explicitly. `BaseSensor` SHALL NOT provide a default implementation. The returned dict represents that plugin's API-visible state — only the fields meaningful for that sensor type SHALL be included.

#### Scenario: Plugin serializes its own config fields
- **WHEN** `to_dict()` is called on a sensor
- **THEN** it returns only the fields relevant to that sensor type
- **AND** internal implementation fields (e.g. `message_id`, `cadence_ms`) MAY be excluded

### Requirement: Uniform read signature
All sensor plugins SHALL implement `read(self, step: int = 0) -> Any`. Plugins that ignore `step` SHALL still accept it without error.

#### Scenario: Engine passes current step to all sensors
- **WHEN** the engine reads a sensor during preset execution
- **THEN** the engine SHALL call `plugin.read(step=self._current_step)` unconditionally
- **AND** plugins that ignore `step` SHALL return their value without error

#### Scenario: Scripted-mode sensor uses step index
- **WHEN** a scripted sensor's `read(step=3)` is called
- **THEN** the sensor SHALL return the value at index `step - 1` in its `scripted_values` list (clamped to valid range)

### Requirement: apply_update strips type and is the single mutation method
`apply_update(data)` SHALL strip the `type` key before applying fields. There is no separate `apply_overrides` method — `apply_update` covers both preset override application and API update requests.

#### Scenario: Preset override with type field is applied correctly
- **WHEN** `apply_update({"type": "color", "value": "RED"})` is called
- **THEN** `type` SHALL be ignored
- **AND** `value` SHALL be applied to the sensor config

### Requirement: No duck-typing in the engine or registry
The engine (`engine.py`) and sensor registry (`sensor_registry.py`) SHALL NOT use `hasattr()`, `getattr()` with fallback, or `try/except` to probe sensor capabilities.

#### Scenario: Engine applies sensor updates via update()
- **WHEN** a preset step specifies `sensorUpdates: {color-left: RED}`
- **THEN** the engine SHALL call `sensors["color-left"].update("RED")` directly

#### Scenario: Registry clones sensors via clone()
- **WHEN** the registry builds the sensor map for a preset
- **THEN** it SHALL call `plugin.clone()` for every default sensor with no try-except surrounding the call

## Requirements (MqttSensor)

### Requirement: MqttSensor publishes via mqtt_message()
Sensors that publish over MQTT SHALL implement `MqttSensor` with a single method `mqtt_message(self) -> tuple[str, str] | None`. The sensor returns `(topic, payload)` if it has something to publish given its current config, or `None` to skip. The engine does not build payloads.

#### Scenario: Sensor with value publishes
- **WHEN** `mqtt_message()` is called on a sensor whose current value is set
- **THEN** it returns a `(topic, payload)` tuple
- **AND** the payload is a JSON string constructed entirely by the sensor

#### Scenario: Sensor with no value skips
- **WHEN** `mqtt_message()` is called on a sensor whose value is `None`
- **THEN** it returns `None`
- **AND** the engine does not publish anything for that sensor

#### Scenario: Engine triggers all MqttSensor plugins
- **WHEN** a preset step has `triggerMqtt: true`
- **THEN** the engine SHALL iterate all sensors, call `mqtt_message()` on each `MqttSensor`
- **AND** publish via `MqttPublisher.publish_raw(topic, payload)` for each non-None result
