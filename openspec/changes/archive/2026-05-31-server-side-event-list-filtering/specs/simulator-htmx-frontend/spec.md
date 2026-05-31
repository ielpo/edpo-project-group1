## MODIFIED Requirements

### Requirement: htmx-driven page shell
The service SHALL serve a `base.html` page at `GET /` that loads htmx and the SSE extension from CDN and uses `hx-get` with `hx-trigger="load"` to fetch each panel fragment on initial page load.

The page shell SHALL treat the event-panel filter mode as a request parameter. The selected mode SHALL default to `full`, SHALL accept `process` when explicitly requested, and SHALL be threaded into both the event-panel fragment request and the existing page-wide SSE connection used for live updates.

When the operator changes filter mode without reloading the page, the frontend SHALL update the current browser URL using `history.replaceState` and SHALL reconnect the existing page-wide SSE stream with the selected `filter` parameter so live updates continue in the same mode.

#### Scenario: Browser loads the simulator UI
- **WHEN** a browser navigates to `GET /`
- **THEN** the page shell is returned
- **AND** all panel fragments are fetched and injected via htmx on load
- **AND** the SSE connection is established for live updates
- **AND** the event panel is requested with the default `full` filter mode

#### Scenario: Browser loads a process-filtered simulator UI
- **WHEN** a browser navigates to `GET /?filter=process`
- **THEN** the page shell is returned with the event-panel fragment request targeting process mode
- **AND** the SSE connection is established with the same process filter mode
- **AND** subsequent event-panel updates use that same selected mode until the operator changes it

#### Scenario: Operator changes filter mode in place
- **WHEN** the operator changes the event-panel filter without reloading the full page
- **THEN** the current browser URL is replaced with the selected `?filter=` value rather than pushing a new history entry
- **AND** the existing page-wide SSE connection is re-established with that same selected filter mode
- **AND** subsequent SSE updates for the event panel use the new selected mode

### Requirement: Event-panel filter toggles
The simulator events panel SHALL provide explicit filter toggles for `Full log` and `Process view`.

The selected filter SHALL control which events the server renders without removing any entries from backend full history. Toggle interactions SHALL select a server-backed filter mode rather than relying on client-side hiding of already-rendered events as the primary behavior.

#### Scenario: Operator switches to process view
- **WHEN** the operator selects `Process view` in the events panel
- **THEN** the resulting event-panel request carries the `process` filter mode
- **AND** the returned panel shows only process-relevant event types (`KAFKA`, `COMMAND`, `PENDING_ACTION`, `ACTION_RESOLVED`, `SENSOR_REQUEST`)
- **AND** non-process events (for example `REST`, `STATE`, `MQTT`) are excluded from the rendered result
- **AND** the full simulator page is not reloaded to apply the filter change
- **AND** live SSE refreshes continue rendering the event panel in process mode until the filter changes

#### Scenario: Operator switches back to full log
- **WHEN** the operator selects `Full log` in the events panel
- **THEN** the resulting event-panel request carries the `full` filter mode
- **AND** the returned panel shows the complete chronological event stream including `MQTT` and other debugging signals
- **AND** the full simulator page is not reloaded to apply the filter change
- **AND** live SSE refreshes continue rendering the full event list until the filter changes