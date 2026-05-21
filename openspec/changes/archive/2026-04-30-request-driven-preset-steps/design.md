## Context

The simulated factory service runs presets as scripted sequences where each step advances after a fixed `delayMs`. This is purely time-driven — the engine never waits for `dobot-control` or Camunda to issue requests. As a result, when used as a test harness, the preset races ahead of the BPMN process: sensor values update before Camunda has had a chance to read them, making reproducible integration testing impossible.

The existing `PendingAction` / `asyncio.Event` gating mechanism handles interactive approval of dobot commands but is orthogonal to step advancement — it blocks a caller but does not advance the preset.

## Goals / Non-Goals

**Goals:**
- Steps with `awaitRequest` declared hold until a matching incoming API request is received
- Sensor values and distance publications for a gated step are applied at the moment the gate fires (inside the request handler), so the caller observes the correct state
- `delayMs` on gated steps acts as a maximum timeout; the step auto-advances (with a warning event) if no matching request arrives in time
- Non-gated steps keep their existing time-delay behaviour unchanged
- `presets.yml` can be updated per-step without code changes

**Non-Goals:**
- No changes to the Camunda BPMN or `dobot-control` service
- No persistence — gates are in-memory only
- No support for gating on Kafka messages (only HTTP request paths)
- No UI changes to the HTMX frontend (step pipeline visualizer already works)

## Decisions

### Decision 1 — Gate condition expressed as a request path pattern

Each step declares `awaitRequest` as an object with a `method` and `path` (supporting `{name}` wildcards matching the existing route structure):

```yaml
- name: pickup
  delayMs: 5000        # timeout
  publishDistance: 12.5
  awaitRequest:
    method: POST
    path: /api/dobot/{name}/commands
```

**Rationale**: HTTP path + method is the natural identifier for "Camunda did X". Alternatives considered:
- _Event type string_ (e.g., `awaitEvent: COMMAND`) — less precise, multiple event types share a type string
- _Arbitrary predicate in YAML_ — too complex, requires a mini-language

### Decision 2 — Gate is an `asyncio.Event` stored on the engine per step

When `_execute_preset` reaches a step with `awaitRequest`, it creates an `asyncio.Event` stored in `self._step_gate` (replacing any previous gate). The HTTP middleware checks after every non-health request whether the path/method matches the active gate; if it does, it sets the event and applies that step's sensor/distance side-effects.

```
_execute_preset:
  step N (gated):
    set self._step_gate = (pattern, event, step)
    await asyncio.wait_for(event.wait(), timeout=step.delayMs/1000)
    # returns once gate fires OR timeout
    clear self._step_gate

HTTP middleware (or route handler):
  if self._step_gate and request matches:
      apply step sensor updates + publishDistance
      event.set()
```

**Why middleware over route handler**: The side-effects (sensor update, distance publish) must happen on the specific request that fires the gate. Doing it in middleware keeps `_execute_preset` unaware of which route caused the advance — the engine only specifies a pattern.

**Alternative**: React purely inside route handlers (Option 3 as discussed). Rejected because it requires every handler to import and call step-advancement logic, scattering the state machine across files.

### Decision 3 — `delayMs` repurposed as gate timeout on gated steps

On steps with `awaitRequest`, `delayMs` is the `asyncio.wait_for` timeout. If it expires the engine emits a `STATE` event with `{"gateTimedOut": true}` and advances regardless — this preserves test resilience.

On non-gated steps `delayMs` retains its current sleep semantics. This is backward-compatible with all existing presets.

### Decision 4 — Sensor/distance side-effects move into the gate-fire path

Currently `_execute_preset` applies `sensorUpdates` and calls `distance_publisher.publish()` before the sleep. For gated steps this order inverts: the middleware fires the event **and** applies the side-effects atomically so the request that triggered the gate gets the updated state in its response (or at minimum, sees it on the very next sensor read).

```
                 BEFORE              AFTER (gated steps)
step N:    apply sensors             hold at gate
           sleep(delayMs)            ← request arrives
                                     apply sensors + publish distance
                                     gate fires → advance
```

## Risks / Trade-offs

- **Concurrent requests**: If two requests arrive simultaneously matching the gate pattern, the first fires the event; the second is a no-op (event already set). No data race because `asyncio.Event.set()` is idempotent and the single-threaded asyncio loop serialises handlers.

- **Middleware overhead**: Every non-health request checks the gate pattern. Cost is a regex match per request — negligible.

- **Gate cleared on stop/reset**: `stop()` and `reset()` must clear `_step_gate` to avoid stale events blocking a future run. → Mitigation: add `self._step_gate = None` in both methods.

- **`publishDistance` on gate-fire is async**: The middleware is sync-context in FastAPI's middleware chain but `distance_publisher.publish()` is a coroutine. → Mitigation: schedule it with `asyncio.create_task()` from the middleware, same pattern used elsewhere.

- **Preset YAML backward compatibility**: Existing steps without `awaitRequest` are unaffected. The new field is optional and defaults to `None`.

## Open Questions

- Should the gate match only on path prefix, or exact path? (Recommendation: exact match with `{name}` wildcard expansion, consistent with FastAPI route matching.)
- Should there be a maximum configurable timeout per-step in addition to `delayMs`? (Out of scope for now — `delayMs` is sufficient.)
