## Why

Testing the full order flow against the physical factory is expensive and error-prone.
The simulated factory currently runs scenarios deterministically, but there is no way to inject real-time human judgment — developers cannot choose, step by step, whether a robot command succeeds or fails during a live integration test.

## What Changes

- Add an **interactive mode** to the simulation engine: a configurable set of command types that are intercepted before auto-resolution.
- When a command matching an intercepted type arrives at `POST /api/dobot/{name}/commands`, the engine suspends the response and queues a `PendingAction`.
- The operator resolves the action (success or failure) through the UI or API; the suspended command response is then completed with the chosen outcome.
- Actions that are not resolved within a configurable timeout are automatically failed.
- New endpoints to read/write the interactive configuration and to list/resolve pending actions.
- The existing JSON API contract (`/api/*`) is preserved — `dobot-control` requires no changes except an increased HTTP timeout when interactive mode is active.

## Capabilities

### New Capabilities

- `interactive-command-gating`: Selective interception of Dobot command types, a pending-action queue, resolution API, and timeout-based auto-failure.

### Modified Capabilities

- `simulated-factory-service`: Existing dobot command handling gains an optional blocking path; the response shape for `POST /api/dobot/{name}/commands` is extended with an `outcome` field when interactive mode is active.

## Impact

- **`services/simulated-factory/simulated_factory/engine.py`**: `handle_dobot_commands` gains the gating logic and `asyncio.Event`-based suspension.
- **`services/simulated-factory/simulated_factory/models.py`**: New `InteractiveConfig` and `PendingAction` models.
- **`services/simulated-factory/simulated_factory/api.py`**: Three new route groups (`/api/interactive/config`, `/api/interactive/pending`, `/api/interactive/{id}/resolve`).
- **`services/simulated-factory/web/index.html`**: New pending-actions panel in the existing UI.
- **`openspec/specs/simulated-factory-service/spec.md`**: Extended with interactive-mode requirements.
- **`dobot-control`**: No code changes required; HTTP client timeout may need raising in local development configuration.
