## Context

The simulated-factory service currently models sensors with two operator-visible control paths: a manual `fixed` value and a `scripted` mode backed by per-sensor `scripted_values`. The twin panel exposes both paths directly, even though preset execution already provides the canonical scripted flow through step-level `sensorUpdates`.

This leaves three separate contracts to maintain together: the frontend forms, the sensor update API, and the sensor plugin runtime semantics. It also makes preset behavior less obvious to an operator because the UI presents editable scripted configuration even while preset execution is the actual source of truth during a run.

## Goals / Non-Goals

**Goals:**
- Reduce the sensor UI to the minimum operator actions needed during normal simulator use.
- Make preset lifecycle the only source of scripted sensor behavior.
- Keep live sensor values visible during a preset run while preventing manual interference.
- Shrink the config and API surface by removing `mode` and `scripted_values` from the public contract.
- Preserve existing sensor integrations such as MQTT publishing while preset-driven values are active.

**Non-Goals:**
- Redesign the overall twin panel layout or unrelated simulator panels.
- Change how preset steps are authored beyond relying on existing `sensorUpdates`.
- Introduce per-sensor locking rules; the lock follows overall preset run state.
- Add a new API version or compatibility shim for the removed scripted sensor fields.

## Decisions

### Decision: Sensor mode becomes implicit runtime state derived from preset lifecycle

Sensors start in manual-control state using their configured default value. Starting a preset moves all sensors into preset-driven read-only behavior, and completing or stopping a preset restores manual control.

Rationale:
- Matches the operator mental model resolved during exploration: idle means editable, running means scripted.
- Eliminates the need for a user-facing mode toggle and for persisting a runtime mode in config.

Alternatives considered:
- Keep the mode dropdown but remove scripted-values editing. Rejected because it still exposes two control models in the UI.
- Keep configured `mode` in `config.yml` and only hide it in the UI. Rejected because hidden state would still complicate the backend contract.

### Decision: Preset step `sensorUpdates` become the only scripted sensor driver

Per-sensor `scripted_values` are removed from the config and model schema. The only scripted sensor progression comes from preset steps applying explicit sensor updates while a run is active.

Rationale:
- Removes redundant sequencing mechanisms.
- Keeps scripted behavior attached to the scenario that needs it.
- Aligns the backend contract with what operators actually observe during preset execution.

Alternatives considered:
- Preserve `scripted_values` for non-preset autonomous sequencing. Rejected because that capability is not needed for the intended simulator workflow and keeps extra API and validation paths alive.

### Decision: The twin fragment remains server-driven and SSE-refreshed for both value and lock state

The twin template keeps one manual form per sensor, but those forms now render only manual value fields. While `state.status == 'running'`, the form controls render disabled and visually muted, while the fragment continues to display the live sensor value from the shared runtime snapshot.

Rationale:
- Reuses the existing fragment + SSE architecture instead of adding client-side state machines.
- Ensures the displayed lock state and sensor value come from the same server-side snapshot.

Alternatives considered:
- Manage lock state entirely in browser-side JavaScript. Rejected because it would duplicate simulator state derivation and risk UI drift.

### Decision: Runtime sensor updates are rejected while a preset is running

`PUT /api/config/sensors/{sensorId}` accepts only manual-value fields and returns `423 Locked` whenever a preset is active.

Rationale:
- Preserves deterministic preset execution.
- Gives API clients a clear failure mode instead of silently ignoring writes.

Alternatives considered:
- Allow manual writes to override preset-driven values. Rejected because it breaks the preset as the source of truth.
- Silently ignore writes during a run. Rejected because the caller would not know the update failed.

### Decision: Sensor plugins expose current value only

The sensor interface no longer computes values from a `step` argument. The engine applies preset sensor updates into live sensor state, and sensor reads return the current stored value.

Rationale:
- Moves sequencing logic to the engine and preset runner where run lifecycle already exists.
- Simplifies sensor implementations and removes clamped indexed-read behavior.

Alternatives considered:
- Keep the `step` parameter but ignore it. Rejected because it preserves a misleading interface after scripted indexing is removed.

## Risks / Trade-offs

- [Breaking contract for config and sensor update API] → Mitigation: document the removals in the delta specs, update config examples, and replace legacy tests with coverage for locked-write rejection.
- [Operators may expect the pre-run manual value to return after completion] → Mitigation: render the live value clearly during runs and specify that completion or stop retains the last preset-applied value.
- [Removing per-sensor scripted values reduces flexibility for ad hoc non-preset demos] → Mitigation: keep preset authoring lightweight and rely on preset `sensorUpdates` for scripted scenarios.
- [Lock state depends on shared simulator status] → Mitigation: keep lock rendering server-side in the twin fragment so UI state follows the same snapshot used elsewhere.

## Migration Plan

1. Update the simulated-factory sensor models, registry, engine, and plugin interfaces to remove `mode`, `scripted_values`, and step-indexed reads.
2. Update `config.yml` examples and defaults to keep only manual sensor value fields plus static metadata.
3. Update the twin fragment and related frontend tests to remove scripted controls and disable manual inputs during runs.
4. Replace scripted-mode API tests with coverage for idle manual updates, run-time `423 Locked`, and retained post-run sensor values.
5. Roll back, if necessary, by reverting the change as one unit; partial rollback would leave the frontend and API contracts inconsistent.

## Open Questions

None at proposal time.