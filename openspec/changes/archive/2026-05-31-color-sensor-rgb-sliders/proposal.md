## Why

The simulated factory twin currently exposes color sensors as a select plus three numeric inputs and distance sensors as plain numeric inputs, but the form cannot keep those controls synchronized without ad hoc browser logic and the backend still treats color `raw_color` more like normalized channels than true RGB values. The operator workflow needs a clearer manual-control model that supports slider-based editing, immediate preview round-trips, and a single canonical sensor state at commit time for both color and distance sensors.

## What Changes

- Replace the color sensor raw color number inputs in the twin panel with three stacked RGB sliders.
- Replace the distance sensor numeric input in the twin panel with a single slider covering the inclusive float range `0.0` to `30.0`.
- Add server-driven preview behavior for color and distance sensor controls so preset selection and slider release can rerender the local sensor form before persistence.
- Change color sensor normalization so committed `raw_color` values are true `0-255` RGB values and enum presets map to canonical RGB triplets.
- Validate committed and previewed distance sensor values as floats in the inclusive range `0.0-30.0`.
- Keep `Apply` as the only persistence action for color and distance sensor changes, with a visible unsaved/draft indicator after preview-only updates.
- Define how SSE refresh interacts with unsubmitted preview state and how the twin rerender derives color preset selection, RGB sliders, and distance slider position from committed state.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `simulator-htmx-frontend`: The twin panel color and distance sensor controls and HTMX update flow will change to support slider-based preview rendering, local draft indication, and localized fragment swaps.
- `simulated-factory-service`: The color sensor contract will change to normalize and persist true `0-255` RGB values, and the distance sensor contract will change to validate and preview float slider values in the inclusive range `0.0-30.0`.

## Impact

- Affected UI templates and HTMX interaction in `services/simulated-factory/templates/`.
- Affected color and distance sensor request validation, normalization, and preview/persistence endpoints in `services/simulated-factory/simulated_factory/`.
- Affected tests for API validation, twin rendering, and sensor plugin behavior.
- No new external dependency is required; the change stays within the current FastAPI + Jinja2 + htmx architecture.