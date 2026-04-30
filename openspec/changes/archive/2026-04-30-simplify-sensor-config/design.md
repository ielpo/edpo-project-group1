## Context

The `simulated-factory` service uses a `SensorConfig` model with a `mode` string field (`fixed`, `scripted`, `random`) to describe sensor behavior. In practice, the engine's `_sensor_value` method dispatches on `scripted_values` presence first, then on `mode == "random"`, then falls through to `value`. This means `mode` is not the authoritative dispatch key — `scripted_values` silently overrides it, creating a mismatch between declared intent and runtime behavior. Additionally, `failRate` is declared in the model but never read by the engine.

## Goals / Non-Goals

**Goals:**
- Make `mode` the single authoritative behavioral switch in `_sensor_value`
- Reduce valid modes to `fixed` and `scripted` only
- Remove `failRate` from `SensorConfig` and `SensorUpdateRequest`
- Add runtime validation: `mode: scripted` requires non-empty `scripted_values`
- Keep `presets.yml` and existing tests passing without behavioral regression

**Non-Goals:**
- Introducing new sensor types or new modes
- Changing MQTT, distance publishing, or preset execution logic
- Refactoring unrelated parts of the engine

## Decisions

### D1 — `mode` as the authoritative dispatch key

**Decision**: `_sensor_value` will branch on `mode` only, removing the `scripted_values`-first check.

**Rationale**: The current implicit priority (scripted_values beats mode) is the root of the confusion. Making `mode` the explicit switch aligns the declaration with behavior.

**Alternative considered**: Remove `mode` entirely and infer behavior from `scripted_values` presence. Rejected because `mode` is part of the external API contract and removing it is a larger breaking change.

---

### D2 — Remove `random` mode

**Decision**: Remove `random` as a valid mode value.

**Rationale**: The `random` implementation is not actually random — it returns a deterministic color derived from `sensorId` and preset name. It has no usage in any configured preset or test scenario that requires non-determinism. It also has no UI entry point for distance/IR sensors (already excluded there). Keeping it adds cognitive overhead for no benefit.

**Alternative considered**: Rename to `auto-color` or `preset-derived` to describe it accurately. Rejected because it still has no current use case, and the preset concept is inherently deterministic.

---

### D3 — Remove `failRate`

**Decision**: Remove `failRate` from `SensorConfig` and `SensorUpdateRequest`.

**Rationale**: The field is declared but never read. Keeping unused fields in the API surface implies a contract that doesn't exist.

**Alternative considered**: Implement `failRate` to actually introduce probabilistic failures. Rejected as out of scope — the service is designed for deterministic preset-driven testing, not chaos testing.

---

### D4 — Validation for `scripted` mode

**Decision**: When `mode` is `scripted` and `scripted_values` is empty, `_sensor_value` falls back to `value` (same as `fixed`), without raising an error.

**Rationale**: A hard error would break existing workflows where a sensor is updated incrementally (mode set before values). Silent fallback is consistent with how `fixed` already works and avoids breaking the API mid-preset.

## Risks / Trade-offs

- [BREAKING] `mode: random` removed from API → Any client sending `mode: random` will receive an unexpected result (falls through to `fixed`). Mitigation: no production callers use `random`; document in changelog.
- [BREAKING] `failRate` removed from API → Clients sending `failRate` in `PUT /api/config/sensors/{id}` will have the field silently ignored (Pydantic strips unknown fields). Mitigation: low risk, field was already inert.
- [Regression risk] Existing `mode: scripted` sensors with `scripted_values` populated continue to work correctly as the dispatch logic still reaches the same code path.
