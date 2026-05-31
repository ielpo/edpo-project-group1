# Interactive Command Gating

## REMOVED Requirements

### Requirement: Interactive configuration endpoint
**Reason**: Entire interactive command gating subsystem removed. Replaced by per-step `awaitTrigger: {type: manual}` declarations in preset YAML.
**Migration**: Remove all calls to `GET/PUT /api/interactive/config`. Manual interaction is now declared per-step in preset config, not configured at runtime.

### Requirement: Pending action queue
**Reason**: The concept of a queue of intercepted commands is removed. Only one gate is active at a time (the current step's gate). `PendingAction` is repurposed to display the single active gate's state.
**Migration**: Remove calls to `GET /api/interactive/pending`. Gate state is exposed via `GET /api/status` and SSE UI updates.

### Requirement: Action resolution endpoint
**Reason**: Replaced by `POST /api/gate/fire` and `POST /api/gate/reject`. No action IDs needed since only one gate is active at a time.
**Migration**: Replace `POST /api/interactive/{actionId}/resolve` with `POST /api/gate/fire` (approve) or `POST /api/gate/reject` (reject/abort).

### Requirement: Automatic timeout and failure
**Reason**: Timeout behavior is now defined per-gate via `awaitTrigger.timeoutMs`. Timeout aborts the preset run (fail-fast) rather than auto-resolving as failure.
**Migration**: Set appropriate `timeoutMs` values on `awaitTrigger` declarations. Be aware that timeout now aborts the entire preset, not just the single action.
