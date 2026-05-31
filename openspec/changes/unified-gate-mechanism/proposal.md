## Why

The simulated-factory engine currently has two separate gate mechanisms — `awaitRequest` (HTTP-triggered preset gates) and interactive command gating (intercept+approve/reject). They solve the same fundamental problem (pause execution until an external signal arrives) but share no code, have different timeout semantics, and cannot be extended to non-HTTP sources like Kafka. Unifying them into a single `awaitTrigger` primitive simplifies the engine, removes dead code (`triggerMqtt`, `_DEFAULT_INTERCEPTED`, interactive API surface), and opens the door to Kafka-triggered and manual (UI button) gates without adding new mechanisms.

## What Changes

- **BREAKING** Replace `awaitRequest` field on preset steps with `awaitTrigger: {type, ..., timeoutMs}`
- **BREAKING** Remove all `/api/interactive/*` endpoints and `InteractiveConfig` model
- **BREAKING** Remove `triggerMqtt` field from preset steps
- **BREAKING** Remove `_DEFAULT_INTERCEPTED` frozenset and interception middleware logic
- Add `POST /api/gate/fire` endpoint for manual gate triggers
- Add Kafka gate type — `KafkaObserver` gains ability to fire gates on topic match
- Evolve `PendingAction` model: drop interception-specific fields, add gate metadata (step name, trigger type/spec, timeout)
- Enforce mutual exclusivity: a step has `delayMs` XOR `awaitTrigger` (Pydantic validator)
- Engine exposes single `try_fire_gate(TriggerEvent)` method replacing `fire_gate_if_matches`
- Timeout aborts the preset run (not auto-fire)
- Manual gate reject = abort
- Migrate all existing presets from `awaitRequest`/`delayMs:60000` to new `awaitTrigger` format

## Capabilities

### New Capabilities
- `unified-trigger-gate`: Single gate primitive supporting http, kafka, and manual trigger types with configurable timeout and abort-on-timeout semantics

### Modified Capabilities
- `request-gated-preset-steps`: `awaitRequest` replaced by `awaitTrigger`; timeout now aborts instead of advancing; sensor updates apply immediately (not on gate fire)
- `interactive-command-gating`: Entire capability removed — replaced by `unified-trigger-gate`

## Impact

- `services/simulated-factory/simulated_factory/engine.py` — Major rewrite of gate logic
- `services/simulated-factory/simulated_factory/models.py` — New `TriggerEvent`, evolved `PendingAction`, new `AwaitTrigger` model, remove `InteractiveConfig`/`AwaitRequest`
- `services/simulated-factory/simulated_factory/adapters/kafka_observer.py` — Inject engine reference, fire gates on message
- `services/simulated-factory/config.yml` — All presets migrated to new format
- `services/simulated-factory/simulated_factory/routes/` — Remove interactive endpoints, add `/api/gate/fire`
- `services/simulated-factory/templates/fragments/pending.html` — Show gate info (type, spec, manual buttons)
- Test suite — Existing gate and interactive tests must be rewritten
