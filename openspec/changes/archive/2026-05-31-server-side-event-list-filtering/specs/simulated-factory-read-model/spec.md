## MODIFIED Requirements

### Requirement: Shared runtime snapshot for UI updates
The simulator SHALL provide one runtime snapshot module that assembles the read model for fragment rendering and SSE updates from engine lifecycle state, event history, inventory cache, sensor configuration, and pending-action state.

The runtime snapshot path SHALL accept the selected event filter mode as an explicit input for event-panel rendering. Fragment routes and SSE out-of-band rendering SHALL use the same normalized filter mode for a given request so both surfaces produce the same event list.

When the frontend reconnects the existing page-wide SSE stream after an in-place filter change, the subsequent snapshot-driven event-panel updates SHALL reflect the newly selected normalized filter mode without requiring a full page reload.

#### Scenario: Fragment handlers share one snapshot source
- **WHEN** the HTTP module renders `status`, `presets`, `twin`, `events`, or `pending` fragments
- **THEN** each fragment's view model is assembled through the runtime snapshot module
- **AND** the HTTP module does not recompute those view models by manually calling unrelated getters in each route
- **AND** the `events` fragment uses the selected normalized event filter mode provided for that request

#### Scenario: SSE uses the same snapshot source
- **WHEN** `GET /sse/status` emits the initial out-of-band render or a later update
- **THEN** the rendered HTML is assembled through the same runtime snapshot module used by fragment endpoints
- **AND** the selected event filter mode from the SSE request is normalized with the same rules used by fragment rendering
- **AND** the event-panel HTML in the SSE payload reflects that same normalized filter mode consistently across updates

#### Scenario: Reconnected SSE stream adopts the new filter mode
- **WHEN** the frontend reconnects `GET /sse/status` after the operator changes the event filter in place
- **THEN** the snapshot-driven event-panel HTML in later SSE payloads reflects the newly selected normalized filter mode
- **AND** the backend does not require a full page navigation to render subsequent event-panel updates in that mode