## Context

The simulated-factory service currently manages sensors as hardcoded logic within the engine. Sensors (distance, color, IR) are instantiated and updated based on static configuration in `config.yml`, but the mapping between config definitions and actual sensor implementations is implicit in the engine code. When users need custom sensor behavior, they must modify the core engine. This creates maintenance burden and limits extensibility.

## Goals / Non-Goals

**Goals:**
- Enable users to create custom sensors by writing isolated Python modules without modifying the engine
- Maintain backward compatibility with existing `config.yml` sensor definitions
- Establish a clear interface contract that all sensors must implement
- Make it obvious how to add new sensor types (documentation-friendly)
- Keep configuration-driven sensor registration explicit (plugins listed in `config.yml`, not auto-discovered)

**Non-Goals:**
- Hot-reload capability (plugins load at startup only; restart required for changes)
- Complex dependency management between plugins
- Auto-discovery from a `plugins/` directory (explicit registration only)
- Changes to the HTTP API or preset execution behavior
- Support for plugins in other services at this stage

## Decisions

### Decision 1: Base Sensor Abstract Class
**Choice**: Define a `BaseSensor` class in `simulated_factory/sensors/base.py` that all sensors inherit from.

**Rationale**: Provides a clear interface contract. Tools and IDEs can validate plugin implementations at load time. Reduces boilerplate and makes requirements explicit.

**Alternatives Considered**:
- Protocol/duck typing: Less explicit, harder to validate at runtime
- Separate registry: More complex, doesn't ensure plugins match interface
- Dataclass-based sensors: Insufficient for state-dependent behavior (scripted values, cadence tracking)

### Decision 2: One Sensor Type Per Module
**Choice**: Each sensor type (distance, color, IR, or custom) is a separate `.py` file in `simulated_factory/sensors/`.

**Rationale**: Clear organization, easier to navigate, promotes single-responsibility. Each module imports its own dependencies (e.g., color distance library).

**Directory Structure**:
```
simulated_factory/sensors/
├── __init__.py
├── base.py           # BaseSensor abstract class
├── distance.py       # DistanceSensor plugin
├── color.py          # ColorSensor plugin
├── ir.py             # IRSensor plugin
└── <custom>.py       # User-defined custom sensors
```

### Decision 3: Plugin Registry in Config
**Choice**: Add a `type` field to each sensor definition in `config.yml`. Engine uses `importlib.import_module()` to load the plugin class by convention: `simulated_factory.sensors.<type>.<Type>Sensor`.

**Rationale**: Configuration-driven, explicit (not auto-discovered). Convention-based naming reduces boilerplate. Existing preset definitions remain unchanged.

**Example Configuration**:
```yaml
defaults:
  sensors:
    color-left:
      type: color
      mode: fixed
      value: RED
      raw_color: [1, 0, 0]
    distance-conveyor:
      type: distance
      mode: scripted
      scripted_values: [30.0, 12.5, ...]
      cadence_ms: 250
```

**Naming Convention**:
- Module file: `simulated_factory/sensors/color.py`
- Class name: `ColorSensor`
- Config reference: `type: color`

### Decision 4: Engine Refactoring
**Choice**: Move sensor initialization from hardcoded lookups to a `_load_plugins()` method that:
1. Iterates over sensors in config
2. Extracts `type` field
3. Dynamically imports and instantiates the sensor class
4. Stores instance in `self.sensors` dict
5. Handles missing or invalid plugins with clear error messages

**Rationale**: Centralizes plugin loading, makes it testable and debuggable. Errors caught at startup, not at runtime.

### Decision 5: Sensor Interface Methods
**Choice**: `BaseSensor` defines these abstract methods:
- `read() -> Any`: Return the current sensor value (used in command interception, state queries)
- `update(value: Any) -> None`: Set the sensor value (for preset step updates)
- `to_dict() -> dict[str, Any]`: Serialize for API responses

**Rationale**: Minimal interface supports all current use cases (reading values, updating from presets, serialization). Extensible without API changes.

### Decision 6: Built-in Sensors as Plugins
**Choice**: Convert existing distance, color, and IR sensor logic into plugin modules; they live in `simulated_factory/sensors/` alongside any custom plugins.

**Rationale**: Proves the plugin architecture works; built-in sensors follow the same rules as custom ones. Reduces special cases in engine logic.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Plugin import failures** → Service fails to start if a `type` is misspelled or module missing | Clear error message at startup listing the bad sensor name and expected module path. Document naming convention. |
| **Plugin implementation differences** → Custom sensors might not implement the interface correctly | Provide a template/example custom sensor. Add type checking / linting in CI if needed. Document the interface thoroughly. |
| **Backward compatibility** → Existing config.yml files don't have `type` field | Provide a migration step: detect missing `type` and infer from sensor config keys or provide defaults (distance-conveyor → type: distance). Document migration. |
| **No hot-reload** → Developers must restart service to test sensor changes | Acceptable trade-off for this phase. Document restart requirement. Future enhancement if needed. |
| **Sensor state sharing** → Custom sensors might need access to engine state or other sensors | Pass dependencies explicitly in constructor (e.g., engine reference, event_store). Lazy-load if needed. |

## Migration Plan

1. **Phase 1**: Create base sensor class and abstract out interface from existing engine sensor logic
2. **Phase 2**: Convert built-in sensors (distance, color, IR) to plugin modules with backward-compatible config
3. **Phase 3**: Update engine to load plugins dynamically; support inferring type for existing configs
4. **Phase 4**: Document plugin development guide; create example custom sensor
5. **Rollback**: Keep old engine code path as fallback until sensors fully migrated (not recommended for production)

## Open Questions

- Should plugins be able to declare dependencies on other plugins (e.g., a custom sensor that depends on distance)?
- Should we provide a CLI tool to validate sensor plugins before deployment?
- Do we need to version the BaseSensor interface for future compatibility?
