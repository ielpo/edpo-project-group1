## 1. Models and Validation

- [x] 1.1 Create `AwaitTrigger` Pydantic model with type discriminator and per-type fields (method, path, topic, timeoutMs)
- [x] 1.2 Create `TriggerEvent` dataclass with type discriminator and optional fields
- [x] 1.3 Add `model_validator` to `PresetStep` enforcing `delayMs` XOR `awaitTrigger` mutual exclusivity
- [x] 1.4 Remove `AwaitRequest` model and `awaitRequest` field from `PresetStep`
- [x] 1.5 Remove `InteractiveConfig` model
- [x] 1.6 Remove `triggerMqtt` field from `PresetStep`
- [x] 1.7 Evolve `PendingAction` dataclass: drop `robot_name`, `commands`, `correlation_id`; add `step_name`, `trigger_type`, `trigger_spec`, `timeout_ms`, `started_at`

## 2. Engine Gate Logic

- [x] 2.1 Replace `_await_gate()` with new implementation that reads `awaitTrigger` from current step and waits with `timeoutMs`
- [x] 2.2 Implement `try_fire_gate(event: TriggerEvent)` method with type-matching logic
- [x] 2.3 Implement timeout-aborts-preset behavior (emit error event, terminate run)
- [x] 2.4 Apply sensor updates immediately when entering a gated step (before wait)
- [x] 2.5 Create/update `PendingAction` when gate becomes active; clear on fire/timeout
- [x] 2.6 Remove `_DEFAULT_INTERCEPTED` frozenset and interception logic from `handle_actuator_commands()`
- [x] 2.7 Remove `_interactive_config` state and post-run reset logic

## 3. KafkaObserver Integration

- [x] 3.1 Add engine (or gate-fire interface) injection to `KafkaObserver.__init__`
- [x] 3.2 Call `try_fire_gate(TriggerEvent(type="kafka", topic=record.topic))` on each consumed message alongside existing event recording

## 4. API Endpoints

- [x] 4.1 Add `POST /api/gate/fire` endpoint that fires active manual gate (200) or returns 404
- [x] 4.2 Add `POST /api/gate/reject` endpoint that triggers immediate timeout/abort for active manual gate
- [x] 4.3 Remove `/api/interactive/config` GET and PUT endpoints
- [x] 4.4 Remove `/api/interactive/pending` GET endpoint
- [x] 4.5 Remove `/api/interactive/{actionId}/resolve` POST endpoint

## 5. Preset Migration

- [x] 5.1 Convert all `awaitRequest` steps in config.yml to `awaitTrigger: {type: http, ...}`
- [x] 5.2 Convert manual preset steps (delayMs: 60000 used as interaction window) to `awaitTrigger: {type: manual, timeoutMs: 60000}`
- [x] 5.3 Remove any `triggerMqtt` declarations from preset steps

## 6. UI Templates

- [x] 6.1 Update `pending.html` to render gate info from evolved `PendingAction` (type, spec, buttons for manual)
- [x] 6.2 Show approve/reject buttons only for `type: manual` gates
- [x] 6.3 Show read-only status card for http/kafka gates with trigger details
- [x] 6.4 Update `runtime_snapshot.py` to pass gate state to template context

## 7. Tests

- [x] 7.1 Unit tests for `AwaitTrigger` model validation (type-specific required fields, mutual exclusivity)
- [x] 7.2 Unit tests for `try_fire_gate` matching logic (all type combinations, no-gate, mismatch)
- [x] 7.3 Integration test: HTTP gate fires on matching request during preset run
- [x] 7.4 Integration test: Kafka gate fires on topic message during preset run
- [x] 7.5 Integration test: Manual gate fires via `POST /api/gate/fire`
- [x] 7.6 Integration test: Gate timeout aborts preset
- [x] 7.7 Remove or rewrite tests for removed interactive gating functionality
