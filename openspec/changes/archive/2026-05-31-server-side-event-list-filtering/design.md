## Context

The simulated-factory UI already offers `Full log` and `Process view` in the event panel, and the backend already knows how to filter event history by mode. The current gap is ownership of the selected mode: the frontend can keep filter state locally and hide entries after render, while fragment routes and the SSE out-of-band stream continue to render from whatever mode the server sees for that request.

This creates a dual-source-of-truth problem. The operator can believe the UI is in process mode while the next SSE refresh replaces the panel with markup rendered from full mode, or vice versa. The desired UX also avoids a full page reload when switching filters, but the current code binds `sse-connect` at the page shell rather than the event panel. That means a panel-only swap cannot change live updates unless the client explicitly rebinds the existing SSE stream.

## Goals / Non-Goals

**Goals:**
- Make the selected event filter mode a server-observed request input.
- Keep event fragment rendering and SSE out-of-band updates aligned for the same selected mode.
- Preserve an in-place filter toggle UX without reloading the entire simulator page.
- Preserve existing backend event-history retention and event-type allowlist semantics.
- Keep the change localized to simulated-factory page-shell, fragment-routing, and snapshot wiring.

**Non-Goals:**
- Changing which event types belong to the process-focused allowlist.
- Changing `/api/events` pagination or free-text filtering behavior.
- Introducing persistent per-user preferences beyond the current request URL/state.
- Splitting the event panel onto a dedicated SSE transport separate from the existing page-wide stream.
- Redesigning the overall simulator UI or SSE transport model.

## Decisions

### Decision: Carry the selected mode in request query parameters

The simulator page shell will treat `filter` as a request-scoped value, defaulting to `full` and accepting `process` when explicitly selected. The shell will thread that mode into the event-panel fragment request and the `/sse/status` connection used for live updates.

This makes the selected mode visible to server rendering without inventing a new storage layer. It also gives reconnects and reloads a stable representation of the chosen state.

Alternatives considered:
- Keep `localStorage` plus client-side reapplication after swaps: rejected because the server still renders without authoritative knowledge of the selected mode.
- Add a dedicated session or cookie-backed filter store: rejected because the behavior is transient UI state and does not need cross-session persistence.

### Decision: Keep the toggle in-place with a thin client coordination hook

Changing the event filter will not reload the whole simulator page. Instead, the event-panel interaction will trigger a filtered panel refresh while a small client hook updates the current URL with `history.replaceState` and reconnects the existing page-wide SSE stream using the selected `filter` parameter.

This keeps the server authoritative for rendered content while preserving the desired local UX. The client logic is intentionally narrow: it does not own filtering semantics, but it does coordinate page-level infrastructure that cannot be updated by an event-panel swap alone.

Alternatives considered:
- Full page navigation on every filter change: rejected because the user wants the panel to update without reloading the whole simulator UI.
- A larger HTMX-swappable shell container that owns the SSE binding: rejected because that broadens the change surface beyond the event-panel behavior.

### Decision: Keep filtering in existing snapshot and event-store paths

The implementation will continue to use existing `filter_mode` support in event-store listing and runtime snapshot composition. The change is to ensure the same selected mode reaches both fragment routes and SSE OOB rendering.

Alternatives considered:
- Add a second render-only filter stage in the template: rejected because it recreates the current mismatch between rendered markup and server state.
- Split event rendering into separate endpoints per mode: rejected because the mode is already a parameter and does not need route proliferation.

### Decision: Reuse the existing page-wide SSE stream

The change will keep the existing page-wide SSE stream instead of introducing a dedicated event-panel stream. Filter changes will reconnect that one stream with the new selected mode.

Alternatives considered:
- Create a dedicated event-panel SSE stream: rejected because it introduces a broader architectural change, new lifecycle concerns, and a larger test surface than this filter change needs.
- Keep both server-side filtering and client-side hide/show logic: rejected because duplicated filtering behavior increases drift risk and makes tests ambiguous.

## Risks / Trade-offs

- [Risk] URL-based filter selection is more visible than hidden client storage. → Mitigation: keep the query surface narrow (`full`/`process`) and default invalid values to `full`.
- [Risk] In-place filter changes require client coordination even though filtering semantics are server-owned. → Mitigation: keep the client hook narrowly scoped to `replaceState` plus SSE reconnect, and specify it explicitly in the contract.
- [Risk] Existing UI tests may encode the previous client-side toggle implementation. → Mitigation: update tests to assert filtered fragment requests, URL replacement behavior, and SSE reconnection outcomes rather than DOM-only hiding hooks.
- [Risk] SSE reconnects could still drift if filter normalization differs between page shell and SSE route handling. → Mitigation: use one normalization rule and thread the normalized mode through shell render, fragment render, and OOB render paths.
- [Risk] Reconnecting the page-wide SSE stream briefly restarts unrelated live updates. → Mitigation: keep the existing single-stream architecture and accept the small reconnect cost as the simpler trade-off for a rare operator action.

## Migration Plan

1. Update the spec contract for simulator frontend and shared read-model behavior.
2. Change the simulator shell and event-panel routing to propagate the selected filter mode server-side.
3. Add the thin client hook that replaces the current URL and reconnects the existing page-wide SSE stream when the operator changes filter mode in place.
4. Remove obsolete client-side-only hide/show ownership code while keeping the coordination hook.
5. Validate with focused tests for shell rendering, in-place filtered fragment output, URL replacement behavior, and SSE-consistent event-panel updates.

## Open Questions

- None for the proposal. The main technical choices are now fixed: request-scoped server filtering, in-place panel updates, `replaceState` URL semantics, and reconnection of the existing page-wide SSE stream.