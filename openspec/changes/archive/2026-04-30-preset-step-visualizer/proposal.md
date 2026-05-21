## Why

The preset panel shows each preset as a static card with only a description and a Run button. Once a preset starts, the top bar displays a terse `RUNNING · happy-path · step 2` badge with no context about what that step means or how many remain. Operators cannot tell at a glance how far through a scenario the simulation is or what step is currently executing.

## What Changes

- When a preset is actively running, its card expands to show a horizontal step pipeline (block-diagram style): each step rendered as a labelled node, completed steps marked, the active step highlighted, and remaining steps shown as pending.
- The pipeline is **only rendered while that preset is running**; idle cards show no pipeline, keeping the UI clean.
- The presets fragment already receives SSE-driven OOB updates, so the live highlighting comes for free once the template is enriched.
- `engine.list_presets()` is extended to include step metadata so the template can render node labels without a separate request.
- The presets fragment endpoint and the SSE OOB renderer are updated to pass the current `SimulationState` alongside preset data so the template can determine which step is active.

## Capabilities

### New Capabilities
- `preset-step-visualizer`: Server-rendered step pipeline shown on a running preset card, live-updated via the existing SSE stream. Displays step names as connected block nodes with completed/active/pending visual states using MD3 design tokens.

### Modified Capabilities
- `simulator-htmx-frontend`: The presets panel fragment gains new rendering logic (step pipeline) triggered by simulation state; the fragment endpoint contract is unchanged but the rendered HTML output is enriched when a preset is running.

## Impact

- **`services/simulated-factory/simulated_factory/engine.py`**: `list_presets()` extended to include step names and notes.
- **`services/simulated-factory/simulated_factory/api.py`**: Two call sites pass `state` to the presets fragment renderer.
- **`services/simulated-factory/templates/fragments/presets.html`**: Conditional step pipeline block added inside each preset card.
- **`services/simulated-factory/templates/base.html`**: ~30 lines of MD3-style CSS added for the step pipeline component.
- **`services/simulated-factory/tests/test_api.py`**: Fragment test updated for enriched template context.
- No new endpoints, no Kafka topics, no external dependencies.
