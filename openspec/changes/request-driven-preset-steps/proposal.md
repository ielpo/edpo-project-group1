## Why

Preset runs currently advance through steps on a fixed timer (`delayMs`), ignoring whether Camunda or `dobot-control` have actually issued any requests. This means the simulation races ahead independently, making it impossible to use as a realistic test harness — Camunda sees sensor values that have already changed before it had a chance to react.

## What Changes

- **BREAKING**: `PresetStep` gains an optional `awaitRequest` field. When set, the engine holds at that step until a matching incoming request arrives (or a timeout elapses), rather than advancing after `delayMs`.
- The `_execute_preset` loop is replaced by a passive state machine: each step is *current* until its gate condition is satisfied by an incoming API call.
- `delayMs` is repurposed as a **maximum wait timeout** on gated steps; non-gated steps keep their current time-delay semantics.
- Sensor values and distance publications for a step are applied *when the gate fires* (i.e., in the request handler), so Camunda observes the intended state during the call that triggered the advance.
- The preset loop emits `STATE` events with `waiting` sub-status while holding at a gated step.

## Capabilities

### New Capabilities
- `request-gated-preset-steps`: Preset steps that advance only when a matching incoming HTTP request is received, with a configurable timeout fallback.

### Modified Capabilities
- `simulated-factory-service`: The preset execution contract changes — step advancement is no longer purely time-driven; `delayMs` becomes an optional timeout on gated steps.

## Impact

- `services/simulated-factory/simulated_factory/engine.py` — `_execute_preset` and `handle_dobot_commands`
- `services/simulated-factory/simulated_factory/models.py` — `PresetStep` (new field)
- `services/simulated-factory/presets.yml` — steps that should gate on Camunda requests need `awaitRequest` populated
- `openspec/specs/simulated-factory-service/spec.md` — preset execution contract updated
- No changes to Java services, Kafka topics, or the dashboard
