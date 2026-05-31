## 1. Simplify the sensor runtime contract

- [ ] 1.1 Remove `mode`, `scripted_values`, and step-indexed reads from the simulated-factory sensor models, registry loading, and sensor plugin interfaces.
- [ ] 1.2 Update preset execution so step `sensorUpdates` write directly into live sensor state, retain the last applied value on stop or completion, and continue to reset to defaults on simulator reset.
- [ ] 1.3 Restrict `PUT /api/config/sensors/{sensorId}` to manual-value fields, reject writes with `423 Locked` while a preset is running, and reject removed scripted fields as invalid input.

## 2. Simplify the twin-panel controls

- [ ] 2.1 Remove mode toggles and scripted-value editors from the twin fragment, leaving only manual value controls for color, IR, and distance sensors.
- [ ] 2.2 Render sensor controls as disabled and visually muted while a preset is running, while still showing live current values through the shared runtime snapshot and SSE refresh path.

## 3. Update docs and verification

- [ ] 3.1 Update simulated-factory config examples and developer documentation to reflect manual sensor defaults only and preset-driven scripted behavior.
- [ ] 3.2 Replace legacy scripted-mode tests with coverage for idle manual updates, locked writes during preset runs, retained post-run sensor values, and preset-aware twin rendering.