# Design: UI + API changes

## Overview

Keep `SensorConfig.scripted_values: list[Any]` and `raw_color: list[int]` as the canonical representation. Change the Factory Twin UI to expose these as explicit form fields and update `update_sensor` to accept arrays and to gracefully parse legacy CSV strings.

## UI

- Render `scripted_values` as a sequence of inputs named `scripted_values[]` so the `json-enc` extension encodes them as a JSON array.
- For `raw_color` render three small numeric inputs named `raw_color[]` (R, G, B) so they arrive as an array of three integers.
- Provide minimal add/remove controls for `scripted_values` (client-side JS that duplicates/removes input rows). The MVP can rely on simple DOM operations (no build step required).

Files to modify:

- `services/simulated-factory/templates/fragments/twin.html` — replace the CSV `<input name="scripted_values">` and raw-color CSV input with repeated inputs and add/remove controls.

Example (concept):

```html
<div class="field scripted-list">
  <label>Scripted values</label>
  <div class="items">
    <!-- rendered server-side for each value -->
    <input name="scripted_values[]" value="{{ v }}" type="number" step="any">
  </div>
  <button type="button" class="add-value">Add</button>
</div>

<!-- raw_color -->
<div class="field">
  <label>Raw RGB</label>
  <input name="raw_color[]" value="{{ sensor.raw_color[0] if sensor.raw_color else '' }}" type="number">
  <input name="raw_color[]" value="{{ sensor.raw_color[1] if sensor.raw_color else '' }}" type="number">
  <input name="raw_color[]" value="{{ sensor.raw_color[2] if sensor.raw_color else '' }}" type="number">
</div>
```

## API / Server

- Update `services/simulated-factory/simulated_factory/api.py` in `update_sensor` to coerce incoming `scripted_values`/`raw_color` payload fields:
  - If `scripted_values` is a string, split on commas and coerce tokens to numbers when possible (failing back to strings).
  - If `scripted_values` is a list, coerce string items to numbers where appropriate and filter out empty entries.
  - If `raw_color` is a string, reuse the existing CSV parsing that already exists for `raw_color`.

Pseudo-code (server-side coercion):

```py
raw = payload.get('scripted_values')
if isinstance(raw, str):
    tokens = [t.strip() for t in raw.split(',') if t.strip()]
    payload['scripted_values'] = [parse_number_or_string(t) for t in tokens]
elif isinstance(raw, list):
    payload['scripted_values'] = [parse_number_or_string(t) for t in raw if t not in (None, "")]

def parse_number_or_string(s):
    if isinstance(s, (int, float)):
        return s
    if '.' in s:
        try: return float(s)
        except ValueError: pass
    try: return int(s)
    except ValueError: return s
```

Notes:

- `SensorUpdateRequest` already accepts `scripted_values: list[Any]`, so no model change required.
- Preserve backward compatibility for existing `presets.yml` (CSV-form `scripted_values` remains supported).

## Tests

- Add unit tests validating:
  - `PUT /api/config/sensors/{id}` accepts `scripted_values` as an array of numbers and stores them.
  - `PUT /api/config/sensors/{id}` accepts a CSV string and the server converts to a list.
  - `twin.html` rendering: server-side template shows multiple inputs for pre-populated `scripted_values` (render test or integration assertion).

## Migration

- Update `services/simulated-factory/presets.yml` examples to show array style (optional).
- Document the change in the README/test-plan so users know the UI now exposes individual fields.
