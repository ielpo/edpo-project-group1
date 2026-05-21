## Why

`SensorConfig.mode` is declared but not used as the behavioral switch — `scripted_values` presence silently overrides it, and `failRate` is stored but never read. This creates a confusing gap between what the config expresses and what the engine actually does.

## What Changes

- **Remove** the `random` mode — it produces a pseudo-deterministic color that is not actually random and has no use case in the preset-driven concept.
- **Remove** the `failRate` field from `SensorConfig` and `SensorUpdateRequest` — it is never read by the engine.
- **Fix** `_sensor_value` to branch on `mode` rather than `scripted_values` presence — `mode` becomes the single authoritative dispatch key.
- **Add validation**: `mode: scripted` requires `scripted_values` to be non-empty.
- **Update** the UI template (twin.html) to remove the `random` option from the color sensor mode selector.
- **Update** the spec (`openspec/specs/simulated-factory-service/spec.md`) to reflect the reduced mode set.
- **BREAKING**: `mode: random` and `failRate` are removed from the public sensor API.

## Capabilities

### New Capabilities
<!-- None: this is a simplification, not an expansion -->

### Modified Capabilities
- `simulated-factory-service`: The sensor configuration requirement changes — valid modes are now `fixed` and `scripted` only; `failRate` is removed from the sensor API contract.

## Impact

- `services/simulated-factory/simulated_factory/models.py` — `SensorConfig`, `SensorUpdateRequest`
- `services/simulated-factory/simulated_factory/engine.py` — `_sensor_value`
- `services/simulated-factory/templates/fragments/twin.html` — mode selector for color sensors
- `services/simulated-factory/presets.yml` — no changes needed (existing modes are valid)
- `openspec/specs/simulated-factory-service/spec.md` — update sensor mode requirement
- Tests in `services/simulated-factory/tests/` — update or remove any `random`/`failRate` assertions
