## Tasks

- [x] 1. Enrich `list_presets()` with step metadata in `services/simulated-factory/simulated_factory/engine.py` so each preset dict includes `steps: [{name}]`.
- [x] 2. Pass `state=jsonable_encoder(engine.get_status())` to the presets template in both `fragment_presets()` and `_render_all_oob()` in `services/simulated-factory/simulated_factory/api.py`.
- [x] 3. Add the conditional step pipeline block (with `step--done` / `step--active` / `step--pending` nodes and connectors) to `services/simulated-factory/templates/fragments/presets.html`.
- [x] 4. Add MD3-tokenized CSS for `.step-pipeline`, `.step-node`, and `.step-connector` to the `<style>` block in `services/simulated-factory/templates/base.html`.
- [x] 5. Update existing fragment test and add a new `test_fragment_presets_shows_pipeline_when_running()` in `services/simulated-factory/tests/test_api.py`; ensure all tests pass with `uv run pytest services/simulated-factory/tests/`.

## Implementation Details

### Task 1: Enrich `list_presets()`
In `engine.py`, update `list_presets()` to include `"steps": [{"name": s.name} for s in preset.steps]` per preset.
Acceptance: `GET /api/presets` response includes `steps: [{name: ...}]` for each preset; existing `test_status_and_presets_endpoints` still passes.

### Task 2: Pass simulation state to presets fragment renderers
In `api.py`:
- `fragment_presets()`: pass `state=jsonable_encoder(engine.get_status())` to render.
- `_render_all_oob()`: add `"state": jsonable_encoder(engine.get_status())` to the presets renderer tuple.

Acceptance: `GET /fragments/presets` returns 200; template context includes `state` with `currentPreset`, `currentStep`, `status`.

### Task 3: Add step pipeline HTML
In `templates/fragments/presets.html`, inside the `{% for preset in presets %}` loop, after `<p>{{ preset.description }}</p>`:

```jinja
{% if state.currentPreset == preset.name and state.status == 'running' %}
<div class="step-pipeline">
  {% for step in preset.steps %}
  <div class="step-node {% if loop.index0 < state.currentStep %}step--done{% elif loop.index0 == state.currentStep %}step--active{% else %}step--pending{% endif %}">
    {{ step.name }}
  </div>
  {% if not loop.last %}<div class="step-connector"></div>{% endif %}
  {% endfor %}
</div>
{% endif %}
```

### Task 4: MD3 CSS for step pipeline
Add to `<style>` in `base.html`:

```css
/* ---------- Step pipeline ---------- */
.step-pipeline { display: flex; align-items: center; gap: 0; flex-wrap: wrap; margin: 12px 0 8px; }
.step-node {
  font: var(--md-sys-typescale-label-small);
  padding: 4px 10px;
  border-radius: var(--md-sys-shape-corner-full);
  border: 1.5px solid var(--md-sys-color-outline-variant);
  white-space: nowrap;
  color: var(--md-sys-color-on-surface-variant);
  background: transparent;
  transition: background 0.2s, border-color 0.2s, color 0.2s;
}
.step-node.step--done {
  background: var(--md-sys-color-secondary-container);
  border-color: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
}
.step-node.step--active {
  background: var(--md-sys-color-primary-container);
  border-color: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary-container);
  font-weight: 500;
}
.step-connector { width: 16px; height: 1.5px; background: var(--md-sys-color-outline-variant); flex-shrink: 0; }
```

### Task 5: Tests
- Update `test_fragment_presets_lists_known_presets` if it breaks due to `state` context.
- Add `test_fragment_presets_shows_pipeline_when_running`: start a preset, GET `/fragments/presets`, assert `step-pipeline` and `step--active` appear.
