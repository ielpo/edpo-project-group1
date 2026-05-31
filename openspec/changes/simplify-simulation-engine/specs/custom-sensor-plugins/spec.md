# Custom Sensor Plugins — Delta Spec

## MODIFIED Requirements

### Requirement: Plugin base interface
All sensor plugins SHALL implement a base interface defined in `simulated_factory/sensors/base.py` as an abstract base class `BaseSensor`. The mandatory abstract methods are `read(step: int = 0)`, `update(value: Any)`, and `to_dict()`. The base class SHALL provide default implementations for `clone()`, `to_config()`, and `apply_update(data)`. Plugins MUST NOT rely on `__getattr__` delegation from `BaseSensor`; all external access to sensor state SHALL go through the declared interface methods. There is no `apply_overrides` method — `apply_update` covers both preset override and API update call sites, stripping `type` unconditionally.

#### Scenario: Plugin implements required interface
- **WHEN** a developer creates a custom sensor plugin
- **THEN** the plugin class SHALL inherit from `BaseSensor` and implement `read(step: int = 0)`, `update(value: Any)`, and `to_dict()`
- **AND** the plugin inherits working `clone()`, `to_config()`, and `apply_update()` from the base class unless it overrides them

#### Scenario: Plugin with scripted mode implements step-aware read
- **WHEN** a plugin supports scripted mode
- **THEN** it SHALL implement `read(self, step: int = 0) -> Any` and use `step` to index into its `scripted_values`
- **AND** calling `read()` without a step argument SHALL return the default (step 0) value without error

#### Scenario: Plugin serialization is explicit
- **WHEN** `to_dict()` is called on any plugin
- **THEN** the plugin's own implementation determines the fields returned
- **AND** no base class default exists — the plugin file is the authoritative source for what the sensor exposes

## REMOVED Requirements

### Requirement: Plugin backward compatibility with sensor_loader
**Reason**: `sensors/sensor_loader.py` (`load_sensor()`) is unused. The engine and registry perform their own dynamic import. Having an unused loader creates confusion for new developers about which loading path to follow.
**Migration**: Remove `sensors/sensor_loader.py`. Any code importing from it (none found in-tree) must switch to using `SensorRegistry.make()` or rely on the registry's config-driven loading.
