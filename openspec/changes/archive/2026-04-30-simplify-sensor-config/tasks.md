## 1. Model cleanup

- [x] 1.1 Remove `failRate` field from `SensorConfig` in `models.py`
- [x] 1.2 Remove `failRate` field from `SensorUpdateRequest` in `models.py`

## 2. Engine logic

- [x] 2.1 Rewrite `_sensor_value` to dispatch on `mode` first: `scripted` → step-indexed `scripted_values`; `fixed` (or unknown/default) → `value`
- [x] 2.2 Remove the `mode == "random"` branch from `_sensor_value`
- [x] 2.3 Verify that sensors with `mode: scripted` and empty `scripted_values` silently fall back to `value` (no exception)

## 3. UI template

- [x] 3.1 Remove `"random"` from the mode selector loop in `templates/fragments/twin.html` (color sensor section)

## 4. Spec update

- [x] 4.1 Apply the delta spec to `openspec/specs/simulated-factory-service/spec.md`: update the "Sensor configuration management" requirement to reflect `fixed`/`scripted` only and remove the `failRate` and `random` entries

## 5. Tests

- [x] 5.1 Update any test assertions in `tests/test_engine.py` or `tests/test_api.py` that reference `mode: random` or `failRate`
- [x] 5.2 Add a test asserting `mode: scripted` with populated `scripted_values` returns the step-indexed value
- [x] 5.3 Add a test asserting `mode: scripted` with empty `scripted_values` returns `value` (fallback)
- [x] 5.4 Run the full test suite and confirm it passes
