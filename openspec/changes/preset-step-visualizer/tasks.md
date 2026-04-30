## Tasks

### Task 1: Enrich `list_presets()` with step metadata
**Goal**: Include step names in the preset list so the template can render pipeline nodes.

**Steps**:
1. Open `services/simulated-factory/simulated_factory/engine.py`.
2. In `list_presets()`, add `"steps": [{"name": s.name} for s in preset.steps]` to the returned dict for each preset.

**Estimate**: 15 min

**Acceptance Criteria**:
- `GET /api/presets` response includes `steps: [{name: ...}]` for each preset.
- Existing `test_api.py::test_status_and_presets_endpoints` still passes.

---

### Task 2: Pass simulation state to presets fragment renderers
**Goal**: Make `SimulationState` available to the presets template at render time.

**Steps**:
1. Open `services/simulated-factory/simulated_factory/api.py`.
2. In `fragment_presets()`, change the render call to also pass `state=jsonable_encoder(engine.get_status())`.
3. In `_render_all_oob()`, add `"state": jsonable_encoder(engine.get_status())` to the presets renderer tuple.

**Estimate**: 15 min

**Acceptance Criteria**:
- `GET /fragments/presets` returns 200 without errors.
- Template context includes `state` with `currentPreset`, `currentStep`, and `status` fields.

---

### Task 3: Add step pipeline HTML to presets template
**Goal**: Render the step pipeline block inside the running preset's card.

**Steps**:
1. Open `services/simulated-factory/templates/fragments/presets.html`.
2. Inside the `{% for preset in presets %}` loop, after the `<p>{{ preset.description }}</p>` line, add a conditional block:
   ```
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

**Estimate**: 30 min

**Acceptance Criteria**:
- When a preset is running, its card contains a `.step-pipeline` div with one `.step-node` per step.
- Completed nodes have class `step--done`, active node has `step--active`, pending nodes have `step--pending`.
- No other card contains a `.step-pipeline` element.

---

### Task 4: Add MD3 CSS for step pipeline component
**Goal**: Style the step pipeline using MD3 design tokens already present in `base.html`.

**Steps**:
1. Open `services/simulated-factory/templates/base.html`.
2. Add the following CSS block inside the `<style>` tag (after existing component styles):

```css
/* ---------- Step pipeline ---------- */
.step-pipeline {
  display: flex;
  align-items: center;
  gap: 0;
  flex-wrap: wrap;
  margin: 12px 0 8px;
}
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
.step-connector {
  width: 16px;
  height: 1.5px;
  background: var(--md-sys-color-outline-variant);
  flex-shrink: 0;
}
```

**Estimate**: 30 min

**Acceptance Criteria**:
- The step pipeline renders with visually distinct done/active/pending states.
- Styles use only MD3 CSS custom properties already declared in `base.html`.
- No third-party CSS library added.

---

### Task 5: Update tests for enriched presets fragment
**Goal**: Keep the test suite green after template and API changes.

**Steps**:
1. Open `services/simulated-factory/tests/test_api.py`.
2. Update `test_fragment_presets_lists_known_presets()` to supply a mock or default `state` context if the test client now requires it (check if a `TemplateError` is raised due to undefined `state`).
3. Verify `happy-path` and other preset names are still present in the rendered HTML.
4. Add a new test `test_fragment_presets_shows_pipeline_when_running()`:
   - Start a preset via `POST /api/presets/run`.
   - Call `GET /fragments/presets`.
   - Assert `.step-pipeline` appears in the running preset's card HTML.
   - Assert `.step--active` appears.

**Estimate**: 30 min

**Acceptance Criteria**:
- All existing tests pass.
- New test asserts pipeline is present when running, absent when idle.
- Run with `uv run pytest services/simulated-factory/tests/` — all green.
