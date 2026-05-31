## Why

The simulated-factory sensor UI currently exposes two competing ways to drive sensors: manual value entry and ad hoc scripted mode editing. That makes the operator surface harder to understand and duplicates behavior that already exists in preset execution, while also keeping a larger API and config contract alive than the simulator now needs.

## What Changes

- Simplify the twin-panel sensor UI to focus on manual value entry only.
- Remove the scripted-values editor and explicit fixed or scripted mode toggle from the frontend.
- Make sensor locking and read-only presentation follow preset lifecycle: editable while idle, greyed out while a preset is running, and restored when the run ends.
- Show the live emitted sensor value in the read-only state during preset execution.
- **BREAKING** Simplify the sensor update contract so `PUT /api/config/sensors/{sensorId}` accepts only manual value fields and rejects runtime edits while a preset is running.
- **BREAKING** Remove `mode` and `scripted_values` from sensor defaults in `config.yml`; preset step `sensorUpdates` become the only scripted sensor driver.
- **BREAKING** Remove built-in scripted sensor mode semantics from the simulated-factory service and sensor plugin interface.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `simulated-factory-service`: change the public sensor configuration contract from explicit fixed or scripted modes to preset-driven locking with manual-value updates only.
- `simulator-htmx-frontend`: change the twin-panel sensor controls to remove scripted editing, show live read-only values during preset runs, and rely on preset status to disable manual edits.

## Impact

- Affected code: `services/simulated-factory` sensor models, registry, engine lifecycle hooks, API handlers, templates, and tests.
- Affected APIs: `PUT /api/config/sensors/{sensorId}`, `GET /api/config/sensors`, and the SSE-rendered twin fragment contract.
- Affected configuration: sensor defaults in `config.yml` no longer include `mode` or `scripted_values`.
- Operational effect: preset runs remain able to publish MQTT-backed sensor updates, but operators can no longer alter sensor values through the API or UI while a run is active.