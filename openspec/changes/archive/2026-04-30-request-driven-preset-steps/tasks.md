## 1. Data Model

- [x] 1.1 Add optional `awaitRequest` field to `PresetStep` in `models.py` with sub-fields `method: str` and `path: str`
- [x] 1.2 Add `waitingForRequest` optional field to `SimulationState` in `models.py` (holds the active gate pattern or `None`)

## 2. Engine — Gate Infrastructure

- [x] 2.1 Add `_step_gate` instance variable to `SimulationEngine` (holds a tuple of `(pattern, asyncio.Event, PresetStep)` or `None`)
- [x] 2.2 Add helper method `_matches_gate(method: str, path: str) -> bool` that checks if an incoming request matches the active gate's method and path pattern (supporting `{name}` wildcards)
- [x] 2.3 Add method `fire_gate_if_matches(method: str, path: str) -> bool` that applies side-effects (sensor updates + schedules `publishDistance`) and sets the event if the request matches; returns `True` if fired
- [x] 2.4 Clear `_step_gate` and `state.waitingForRequest` in `stop()` and `reset()`

## 3. Engine — Preset Loop

- [x] 3.1 Update `_execute_preset` so that steps without `awaitRequest` retain existing `asyncio.sleep(delayMs * multiplier)` behaviour (no change)
- [x] 3.2 For steps with `awaitRequest`: set `_step_gate` and `state.waitingForRequest`, then `await asyncio.wait_for(event.wait(), timeout=step.delayMs/1000 * multiplier)`
- [x] 3.3 On `asyncio.TimeoutError` in a gated step: apply sensor updates + publishDistance, emit `STATE` event with `{"gateTimedOut": true}`, then continue to next step
- [x] 3.4 Move sensor updates and `publishDistance` calls for gated steps into `fire_gate_if_matches` (called by middleware); keep existing pre-sleep placement only for non-gated steps
- [x] 3.5 Clear `_step_gate` and `state.waitingForRequest` after a gate fires (success or timeout)

## 4. API Middleware

- [x] 4.1 After every non-health request is handled in `capture_requests` middleware, call `engine.fire_gate_if_matches(request.method, request.url.path)` and discard the return value (gate side-effects happen as a `create_task` coroutine if async)

## 5. Presets YAML

- [x] 5.1 Add `awaitRequest` to the `pickup` step in `happy-path` preset (await `POST /api/dobot/{name}/commands`)
- [x] 5.2 Add `awaitRequest` to the `color-check` step in `happy-path` preset (await `GET /api/dobot/{name}/color`)
- [x] 5.3 Add `awaitRequest` to the `place` step in `happy-path` preset (await `POST /api/dobot/{name}/commands`)
- [x] 5.4 Mirror the same `awaitRequest` additions to `wrong-color` and `pickup-failure` presets for their equivalent steps
- [x] 5.5 Set `delayMs` on gated steps to a sensible timeout (e.g., 10000 ms) that gives Camunda enough time to respond

## 6. Tests

- [x] 6.1 Unit test: non-gated step still advances on timer (no regression)
- [x] 6.2 Unit test: gated step holds until `fire_gate_if_matches` is called with matching method+path
- [x] 6.3 Unit test: gated step advances on timeout and emits `gateTimedOut` event
- [x] 6.4 Unit test: stop/reset while gate is active clears `_step_gate` without hanging
- [x] 6.5 Unit test: `_matches_gate` correctly handles `{name}` wildcard (e.g., `/api/dobot/left/commands` matches `/api/dobot/{name}/commands`)
- [x] 6.6 Unit test: `waitingForRequest` appears in status while gate is held and is cleared after

## 7. Validation

- [x] 7.1 Run the full existing test suite (`uv run pytest`) and confirm no regressions
- [x] 7.2 Manual smoke test: start `happy-path` preset, issue a `POST /api/dobot/left/commands` from curl/Bruno, verify the step advances and sensor state updates
- [x] 7.3 Manual smoke test: let a gated step timeout; verify the `gateTimedOut` event appears in `GET /api/events`
