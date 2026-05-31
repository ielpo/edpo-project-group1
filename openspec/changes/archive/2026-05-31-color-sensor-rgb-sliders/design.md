## Context

The simulated-factory twin currently renders color sensors as a named-color select plus three numeric inputs and distance sensors as a plain numeric input inside the twin panel. Those forms can persist sensor values through `PUT /api/config/sensors/{sensorId}`, but the browser cannot keep related controls synchronized without imperative client logic. At the same time, the backend still treats `raw_color` as normalized channels rather than true RGB bytes, which makes a slider-based color UI misleading and leaves the distance control without an explicit range-based interaction model.

The explored direction keeps the existing server-rendered FastAPI + Jinja2 + htmx architecture and avoids custom browser JavaScript. Color and distance sensors will preview through localized HTML round-trips and persist only when the operator presses `Apply`. The current SSE out-of-band stream remains the source of truth for committed state and lock-state refresh.

## Goals / Non-Goals

**Goals:**
- Render color sensor manual controls as a preset selector plus three stacked RGB sliders, and distance sensor controls as single range sliders.
- Treat `raw_color` as committed `0-255` RGB values end-to-end for color sensors.
- Treat committed distance sensor values as bounded floats in the inclusive range `0.0-30.0`.
- Keep `Apply` as the only persistence action for color and distance sensor state changes.
- Support immediate form synchronization through server-driven preview swaps on preset change and slider release.
- Preserve the existing SSE-based committed-state refresh model for the twin panel.

**Non-Goals:**
- Persist in-progress draft state across SSE refreshes or reconnects.
- Generalize draft-preview behavior beyond color and distance sensors.
- Introduce a client-side state machine or custom JavaScript synchronization layer.
- Change IR sensor editing semantics beyond incidental template refactoring.

## Decisions

### 1. Separate preview rendering from persistence

Preview interactions for slider-based manual controls will use a dedicated HTML fragment endpoint that accepts the current draft form values and returns only the affected color-sensor or distance-sensor card. This keeps preview semantics explicit and avoids overloading `PUT /api/config/sensors/{sensorId}`, which remains the persistence endpoint returning JSON.

The preview endpoint will normalize the draft values server-side and rerender the local fragment with the derived preset selection or slider position and unsaved-state marker. Persistence continues to happen only through `Apply`, which submits the canonical values to the existing `PUT` endpoint and relies on SSE/OOB refresh for the committed twin state.

Alternatives considered:
- Reuse the existing `PUT` endpoint with a preview flag: rejected because it mixes HTML preview and JSON persistence semantics into one route.
- Use custom JavaScript to synchronize the form locally: rejected because the change explicitly aims to stay within server-rendered HTMX interactions.

### 2. Make color sensor `raw_color` true RGB bytes

For color sensors, committed `raw_color` will become a three-element `0-255` RGB triple. Canonical preset mappings are:
- `RED` -> `[255, 0, 0]`
- `GREEN` -> `[0, 255, 0]`
- `BLUE` -> `[0, 0, 255]`
- `YELLOW` -> `[255, 255, 0]`

Named-color selection writes the canonical RGB triple. Manual slider edits submit the current RGB draft directly. The rendered preset selector is derived from the current RGB triple by exact canonical match; non-canonical values render as `(none)`.

Alternatives considered:
- Keep internal `0/1` channels and only change the UI: rejected because it makes RGB sliders deceptive.
- Track a persistent manual/provenance flag so manually-entered canonical values still render as `(none)`: rejected because it adds state complexity without improving the committed contract.

### 3. Represent distance sensors as bounded floating-point sliders

Distance sensors will use one slider-backed `value` control with an inclusive range of `0.0-30.0`. Preview and persistence paths will accept floating-point values only within that interval, and values outside the supported range will be rejected by validation rather than silently clamped.

Manual slider edits submit the current float draft directly. The rendered slider position is always derived from the current committed or previewed numeric value, and the same localized preview/unsaved-marker behavior used for color sliders applies to distance sliders.

Alternatives considered:
- Keep the existing numeric input: rejected because it would leave distance sensors inconsistent with the rest of the slider-based twin interaction model.
- Silently clamp out-of-range values: rejected because explicit validation gives a clearer contract and avoids hiding incorrect requests.

### 4. Keep preview state localized and ephemeral

Preview round-trips will swap only the affected color-sensor or distance-sensor card or form, not the whole twin panel. This keeps the UI responsive, reduces markup churn, and isolates draft feedback to the control the operator is editing. The previewed form will show an unsaved indicator attached to the `Apply` action.

Preview state lives only in the returned HTML fragment. If an SSE update arrives before `Apply`, the draft may be replaced by the committed twin panel state. This is an intentional trade-off to avoid server-side draft storage or client-side reconciliation logic.

Alternatives considered:
- Rerender the entire twin panel on each preview: rejected because it is noisier and more fragile under live updates.
- Persist draft state server-side between requests: rejected because it adds session-like complexity to a currently stateless UI flow.

### 5. Keep locking and committed refresh behavior aligned with the current twin model

The twin panel will continue to derive editability from simulation status. While a preset is running, color and distance slider controls remain disabled in committed twin fragments and no preview interaction is expected from the UI. The committed `Apply` path will keep using `hx-swap="none"` plus SSE/OOB refresh, which preserves the current source-of-truth model for saved state.

Alternatives considered:
- Let preview requests bypass lock-state rules: rejected because it creates a mismatch between editable draft state and the committed simulator state.

## Risks / Trade-offs

- [Preview drafts disappear on SSE refresh] -> Accept ephemeral drafts and document the behavior in the UI design and tests.
- [Preview and persistence normalization could diverge] -> Reuse the same server-side normalization helper for preview rendering and `PUT` processing.
- [Changing `raw_color` semantics may affect downstream compatibility] -> Keep the response shape unchanged and update color compatibility requirements plus tests to assert `0-255` semantics.
- [Distance sliders can expose float precision noise] -> Use one shared formatting/validation path so preview and committed renders show consistent values.
- [More fragment endpoints increase template surface area] -> Limit the preview endpoint to slider-based controls only and share the same partial rendering logic used by the twin fragment.

## Migration Plan

There is no persisted-data migration because simulator sensor edits are runtime-only. Implementation should:
- add server-side RGB normalization helpers, distance range validation helpers, and updated sensor serialization,
- add the preview fragment endpoint and localized template partials,
- update twin rendering to use RGB and distance sliders plus unsaved-state markers,
- extend API, rendering, and plugin tests,
- update simulator documentation to describe the new draft/preview behavior.

Rollback is straightforward: remove the preview endpoint and template partials, restore the previous numeric inputs, and revert RGB normalization and distance slider validation to the prior behavior.

## Open Questions

No blocking design questions remain for the proposed implementation. The exact fragment path and template factoring can be chosen during implementation as long as the preview contract stays separate from `PUT /api/config/sensors/{sensorId}` and only the touched color-sensor or distance-sensor control swaps during preview.