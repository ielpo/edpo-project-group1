## 1. Backend Slider Sensor Contract

- [x] 1.1 Add shared normalization and validation helpers for canonical named colors, `0-255` RGB triples, and distance values in the inclusive `0.0-30.0` range.
- [x] 1.2 Update color sensor validation and persistence so `raw_color` is stored and returned as three `0-255` channel values.
- [x] 1.3 Update distance sensor validation and persistence so slider-backed values are accepted only within the inclusive `0.0-30.0` range.
- [x] 1.4 Update color sensor read/serialization paths to derive the named color only from exact canonical RGB matches.
- [x] 1.5 Add a non-persistent preview endpoint for slider-based sensor controls that normalizes draft values and returns the localized HTML fragment without mutating committed sensor state.

## 2. Twin Panel UI

- [x] 2.1 Extract or add reusable slider-based sensor fragments for color and distance sensor cards in the twin panel.
- [x] 2.2 Replace the color sensor raw numeric inputs with three stacked RGB sliders and a `(none)`-capable named-color selector.
- [x] 2.3 Replace the distance sensor numeric input with a slider covering the inclusive float range `0.0-30.0`.
- [x] 2.4 Wire preview requests from preset changes and slider release to swap only the touched color-sensor or distance-sensor fragment.
- [x] 2.5 Keep `Apply` as the only persistence action, with `hx-swap="none"` on the `PUT` flow and an unsaved-state marker after preview-only changes.

## 3. Validation And Documentation

- [x] 3.1 Extend API and validator tests for canonical named-color mapping, `0-255` RGB coercion, distance range validation, and preview normalization.
- [x] 3.2 Extend twin/template tests for RGB slider rendering, distance slider rendering, localized preview swaps, and draft reset on SSE rerender.
- [x] 3.3 Update simulated-factory documentation to describe the slider workflow, preview behavior, and committed-state semantics for color and distance sensors.