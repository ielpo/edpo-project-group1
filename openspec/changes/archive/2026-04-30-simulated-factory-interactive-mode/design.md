## Context

The simulated factory engine currently resolves all Dobot commands immediately and deterministically. Developers working on `dobot-control` flows can only reproduce failure paths by pre-configuring sensor overrides before a run — there is no way to inject a decision mid-flight. Interactive mode introduces an operator-controlled gate: selected command types are suspended until a human approves or rejects them via the UI or API.

The existing command path in `engine.handle_dobot_commands` updates `DobotRuntimeState` synchronously and returns a `correlationId`. The new path must suspend the HTTP response without blocking the asyncio event loop, deliver a notification to connected UI clients, and complete the response once the operator acts (or a timeout fires).

## Goals / Non-Goals

**Goals:**
- Allow operators to configure which Dobot command types are intercepted at runtime.
- Suspend `POST /api/dobot/{name}/commands` responses for intercepted types until resolved.
- Expose a resolution API (`POST /api/interactive/{id}/resolve`) accepting `success` or `failure`.
- Auto-fail pending actions after a configurable timeout (default 30 s).
- Propagate resolution outcome in the command response so callers can react.
- Notify connected WebSocket / SSE clients when a pending action is created or resolved.

**Non-Goals:**
- Modifying the `dobot-control` service code (only its HTTP timeout setting may need adjustment).
- Persisting interactive configuration across process restarts.
- Intercepting MQTT or Kafka messages — only HTTP commands to the simulator.
- Simulating partial / mixed outcomes within a single command batch.

## Decisions

### D1 — asyncio.Event for suspension

Each `PendingAction` holds an `asyncio.Event`. The `handle_dobot_commands` coroutine calls `asyncio.wait_for(event.wait(), timeout)` after queuing the action. The resolution endpoint sets the event and stores the outcome. This keeps the suspension fully within the asyncio event loop with no threads or external queues.

**Alternatives considered:**
- `asyncio.Queue` (consumer/producer) — more complex, no advantage here since there is exactly one waiter per action.
- Background task + polling — unnecessary round-trips, harder to propagate the outcome back.

### D2 — Interactive config stored in engine memory

`InteractiveConfig` (intercepted command types set + timeout) lives on the `SimulationEngine` instance. It is not persisted. A `PUT /api/interactive/config` replaces the runtime config.

**Alternatives considered:**
- Persisting to `presets.yml` — adds write complexity, unnecessary for a dev tool.
- Environment variable only — prevents runtime reconfiguration without restart.

### D3 — Command response extended with outcome field

When interactive mode resolves a command, `POST /api/dobot/{name}/commands` returns `{"correlationId": "...", "outcome": "success"|"failure"}`. In non-interactive mode the `outcome` field is omitted, preserving backward compatibility.

**Alternatives considered:**
- Separate polling endpoint for outcome — requires `dobot-control` to poll; more complex.
- WebSocket push to `dobot-control` — `dobot-control` has no WS client; HTTP long-poll is simpler.

### D4 — Batch command interception strategy

When a batch of commands arrives (`[cmd1, cmd2, cmd3]`) and one or more types are intercepted, the **entire batch** is held as a single `PendingAction`. The operator sees all commands in the batch and resolves the whole batch as success or failure. Partial batch resolution is not supported (Non-Goal).

**Rationale:** `dobot-control` sends movement commands as atomic batches; splitting them mid-flight would leave the simulated robot in an undefined intermediate state.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| `dobot-control` HTTP client times out before operator resolves | Document that the `dobot-control` HTTP timeout must be set above the interactive timeout. Default interactive timeout is 30 s; `dobot-control` should use ≥ 35 s. |
| Long-held asyncio events leak if a client disconnects | `asyncio.wait_for` with timeout ensures events are always released. Engine tracks pending actions in a dict and cleans up on resolution or timeout. |
| Multiple simultaneous pending actions confuse operators | UI displays pending actions as a queue ordered by arrival time. Each action shows robot name, command types, and target values. |
| Interactive mode left enabled in CI | Config is in-memory and resets on restart. Document that CI should not enable interactive mode. |

## Migration Plan

Backward compatible. The new endpoints are additive. Interactive mode is **disabled by default** (empty intercepted set). No migration steps required.

## Open Questions

- Should the resolution API accept an optional `reason` string for audit logging? (Suggested: yes, optional field.)
- Should a preset run be allowed while there are pending actions? (Suggested: reject with 409 until queue is clear.)
