## Context

The simulated-factory UI is a server-rendered htmx app (FastAPI + Jinja2, MD3 CSS). The presets panel (`#preset-panel`) is already part of the SSE out-of-band update loop: every time the engine emits an event, all panels—including presets—are re-rendered and pushed to the browser. The engine's `SimulationState` carries `currentPreset`, `currentStep`, and `currentStepName`. The `list_presets()` helper currently returns only `{name, description}` per preset, dropping step metadata.

## Goals / Non-Goals

**Goals**
- Show a step pipeline on the card of the actively running preset only.
- Pipeline nodes display step name, with completed/active/pending visual states.
- Live update the pipeline as steps advance (via existing SSE loop, no new endpoint).

**Non-Goals**
- No pipeline shown on idle or non-running preset cards.
- No step notes/tooltips in this change (can be a follow-on).
- No new API endpoints or Kafka topics.

## Architecture Diagram

```
┌── Browser ───────────────────────────────────────────────────────────────┐
│                                                                           │
│  #preset-panel (htmx OOB target)                                         │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  happy-path card                              [Run happy-path]   │    │
│  │  Deterministic successful order flow                             │    │
│  │                                                                  │    │
│  │  [order-received] ──▶ [pickup] ──▶ [color-check] ──▶ [place]   │    │
│  │       ✓                  ✓            ● active          ○        │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  wrong-color card   (idle — no pipeline shown)  [Run wrong-c…]  │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
        ▲  SSE OOB event (text/event-stream)
        │  event: update / data: <rendered HTML fragments>
        │
┌── FastAPI (simulated-factory) ────────────────────────────────────────────┐
│                                                                           │
│  GET /sse/status  ──▶  _render_all_oob()                                 │
│                            │                                              │
│                            ├─ fragments/status.html  (state)             │
│                            ├─ fragments/presets.html (presets + state)  ◀─ changed
│                            ├─ fragments/sensors.html                     │
│                            ├─ fragments/events.html                      │
│                            └─ fragments/pending.html                     │
│                                                                           │
│  SimulationEngine                                                         │
│   .list_presets()  ──▶  [{name, description, steps:[{name}]}]  ◀─ changed│
│   .get_status()    ──▶  SimulationState {currentPreset, currentStep}     │
└───────────────────────────────────────────────────────────────────────────┘
```

## Decisions

### Decision 1: Enrich `list_presets()` vs. a new `get_preset_detail()` call
**Chosen**: Enrich `list_presets()` to include `steps: [{name}]` per preset.  
**Rationale**: The presets fragment already calls `list_presets()` in both the HTTP endpoint and the SSE OOB renderer. Adding a second call per-preset in the template (via a new endpoint) would require either a JS fetch or a template macro that calls back to the server — breaking the server-render model. Including steps in the existing list response is a minimal, in-process change with no latency cost.  
**Alternative**: A separate `GET /api/presets/{name}` detail endpoint — rejected because it requires client-side coordination and adds complexity for no benefit.

### Decision 2: Pass `state` to the presets fragment renderer
**Chosen**: Both `/fragments/presets` endpoint and `_render_all_oob()` pass `jsonable_encoder(engine.get_status())` as `state` to the template.  
**Rationale**: The template needs to know which preset is running and at which step index to render visual states. `get_status()` is already called in the SSE loop for other panels — this is a cheap re-use.

### Decision 3: Pipeline visibility — only when running
**Chosen**: The step pipeline block is wrapped in `{% if state.currentPreset == preset.name and state.status == 'running' %}`.  
**Rationale**: User requirement. Idle cards stay compact; the pipeline only appears for the active preset. This also avoids rendering pipelines for all presets simultaneously, which would be visually noisy.

### Decision 4: CSS approach — inline in `base.html`
**Chosen**: Add step pipeline styles directly to the `<style>` block in `base.html`.  
**Rationale**: Consistent with the existing pattern — the entire stylesheet lives in `base.html`. No build step, no separate CSS file to serve.

## Risks / Trade-offs

- **`currentStep` is 0-indexed count of completed steps** → the template must treat index `i < currentStep` as completed, `i == currentStep` as active, `i > currentStep` as pending. Off-by-one errors are easy to introduce in the Jinja2 `loop.index0` logic. Mitigation: clear spec and a dedicated template test.
- **list_presets() is called per SSE event** — adding step lists increases payload size slightly. With 3 presets of ~4 steps each, the delta is negligible (~300 bytes).
- **No step notes in this change** — the `note` field exists on `PresetStep` but is intentionally excluded to keep scope tight.

## Migration Plan

Pure additive change — no data migration, no breaking API contract changes. Deploy by restarting the simulated-factory service. Rollback by reverting the three changed files and restarting.

## Open Questions

- None blocking implementation.
