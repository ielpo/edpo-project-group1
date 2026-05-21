# Proposal: Split sensor scripted CSV into individual fields

## Summary

Replace single CSV/text `scripted_values` and `raw_color` inputs in the Factory Twin UI with explicit, per-value form fields (array inputs). Update the simulated-factory API to accept array inputs and provide a CSV-string fallback for backward compatibility.

## Motivation

- Improves usability: users can edit individual sensor values without hand-editing CSV strings.
- Stronger validation and typing: numeric distance entries and RGB channels can be validated individually.
- Reduces parse/format errors and makes presets easier to author and migrate.

## Scope

- UI: `services/simulated-factory/templates/fragments/twin.html` (distance & color sensor forms)
- API: `services/simulated-factory/simulated_factory/api.py` (coercion/parsing in `update_sensor`)
- Tests: update/add unit tests in `services/simulated-factory/tests/`
- Examples/docs: `services/simulated-factory/presets.yml`, README and test-plan notes

## Success criteria

- The Factory Twin renders per-value inputs for `scripted_values` and `raw_color`.
- Submitting the form sends arrays to `PUT /api/config/sensors/{sensorId}` and engine receives typed lists.
- Existing CSV-style submissions still work (server-side fallback).
- Tests cover new parsing behavior and UI form serialization expectation.

## Non-goals

- Changing the runtime `SensorConfig` schema (it remains `scripted_values: list[Any]` and `raw_color: list[int]`).
- Implementing a rich client-side editor beyond simple add/remove controls (MVP only).
