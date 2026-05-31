# Request-Gated Preset Steps

## REMOVED Requirements

### Requirement: Gated step declaration in preset YAML
**Reason**: Replaced by `unified-trigger-gate` capability. The `awaitRequest` field is superseded by `awaitTrigger: {type: http, ...}`.
**Migration**: Replace `awaitRequest: {method, path}` with `awaitTrigger: {type: http, method, path, timeoutMs}` on all preset steps. `delayMs` no longer serves as the timeout for gated steps; use `awaitTrigger.timeoutMs` instead.

### Requirement: Gate side-effects applied atomically on gate fire
**Reason**: Replaced by `unified-trigger-gate` requirement "Sensor updates apply immediately on gated steps". Sensor updates now apply *before* the gate wait, not on gate fire.
**Migration**: No code migration needed for consumers of sensor data. Behavior change: sensors reflect step state immediately rather than being deferred until gate fires.

### Requirement: Gate status exposed in simulation state
**Reason**: Replaced by `unified-trigger-gate` requirement "Gate status in simulation state" with richer gate metadata (type, spec, timeout).
**Migration**: Clients reading `waitingForRequest` from `GET /api/status` should adapt to the new gate info structure that includes trigger type and full specification.
