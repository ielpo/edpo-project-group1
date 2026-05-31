## REMOVED Requirements

### Requirement: Sensor form submits via htmx (inline in twin)
**Reason**: The operator UI uses `hx-swap="none"` on sensor forms and relies on SSE out-of-band refresh to update the twin panel. The PUT endpoint no longer returns an HTML fragment for HTMX callers — it always returns JSON. The visual update path is exclusively SSE OOB swap.
**Migration**: No frontend code change required. The twin.html forms already declare `hx-swap="none"` and ignore the response body. The SSE stream continues to push updated twin fragments on every state change.

### Requirement: Sensor form submits via htmx
**Reason**: Duplicate of the inline-in-twin requirement above. Both describe a per-sensor HTML fragment response that no longer exists. The sensor update endpoint always returns JSON; the operator visual refresh happens through the SSE OOB stream.
**Migration**: Same as above — no action needed for the HTMX frontend since it already uses `hx-swap="none"`.

## ADDED Requirements

### Requirement: Sensor update relies on SSE for operator visual refresh
The simulator HTMX frontend SHALL rely exclusively on the SSE out-of-band swap stream for reflecting sensor configuration changes in the operator UI. The sensor form SHALL use `hx-swap="none"` and SHALL NOT depend on the PUT response body for visual updates.

#### Scenario: Operator submits sensor form and sees updated twin
- **WHEN** an operator submits a sensor edit form in the twin panel
- **THEN** the form sends `PUT /api/config/sensors/{id}` with `hx-swap="none"`
- **AND** the SSE stream emits an updated twin panel fragment with `hx-swap-oob="true"`
- **AND** the twin panel reflects the new sensor configuration without using the PUT response body
