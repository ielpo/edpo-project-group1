## 1. Models and Validation

- [ ] 1.1 Create `AwaitTrigger` Pydantic model with type discriminator and per-type fields (method, path, topic, timeoutMs)
- [ ] 1.2 Create `TriggerEvent` dataclass with type discriminator and optional fields
- [ ] 1.3 Add `model_validator` to `PresetStep` enforcing `delayMs` XOR `awaitTrigger` mutual exclusivity
- [ ] 1.4 Remove `AwaitRequest` model and `awaitRequest` field from `PresetStep`
- [ ] 1.5 Remove `InteractiveConfig` model
- [ ] 1.6 Remove `triggerMqtt` field from `PresetStep`
- [ ] 1.7 Evolve `PendingAction` dataclass: drop `robot_name`, `commands`, `correlation_id`; add `step_name`, `trigger_type`, `trigger_spec`, `timeout_ms`, `started_at`

## 2. Engine Gate Logic

- [ ] 2.1 Replace `_await_gate()` with new implementation that reads `awaitTrigger` from current step and waits with `timeoutMs`
- [ ] 2.2 Implement `try_fire_gate(event: TriggerEvent)` method with type-matching logic
- [ ] 2.3 Implement timeout-aborts-preset behavior (emit error event, terminate run)
- [ ] 2.4 Apply sensor updates immediately when entering a gated step (before wait)
- [ ] 2.5 Create/update `PendingAction` when gate becomes active; clear on fire/timeout
- [ ] 2.6 Remove `_DEFAULT_INTERCEPTED` frozenset and interception logic from `handle_actuator_commands()`
- [ ] 2.7 Remove `_interactive_config` state and post-run reset logic

## 3. KafkaObserver Integration

- [ ] 3.1 Add engine (or gate-fire interface) injection to `KafkaObserver.__init__`
- [ ] 3.2 Call `try_fire_gate(TriggerEvent(type="kafka", topic=record.topic))` on each consumed message alongside existing event recording

## 4. API Endpoints

- [ ] 4.1 Add `POST /api/gate/fire` endpoint that fires active manual gate (200) or returns 404
- [ ] 4.2 Add `POST /api/gate/reject` endpoint that triggers immediate timeout/abort for active manual gate
- [ ] 4.3 Remove `/api/interactive/config` GET and PUT endpoints
- [ ] 4.4 Remove `/api/interactive/pending` GET endpoint
- [ ] 4.5 Remove `/api/interactive/{actionId}/resolve` POST endpoint

## 5. Preset Migration

- [ ] 5.1 Convert all `awaitRequest` steps in config.yml to `awaitTrigger: {type: http, ...}`
- [ ] 5.2 Convert manual preset steps (delayMs: 60000 used as interaction window) to `awaitTrigger: {type: manual, timeoutMs: 60000}`
- [ ] 5.3 Remove any `triggerMqtt` declarations from preset steps

## 6. UI Templates

- [ ] 6.1 Update `pending.html` to render gate info from evolved `PendingAction` (type, spec, buttons for manual)
- [ ] 6.2 Show approve/reject buttons only for `type: manual` gates
- [ ] 6.3 Show read-only status card for http/kafka gates with trigger details
- [ ] 6.4 Update `runtime_snapshot.py` to pass gate state to template context

## 7. Tests

- [ ] 7.1 Unit tests for `AwaitTrigger` model validation (type-specific required fields, mutual exclusivity)
- [ ] 7.2 Unit tests for `try_fire_gate` matching logic (all type combinations, no-gate, mismatch)
- [ ] 7.3 Integration test: HTTP gate fires on matching request during preset run
- [ ] 7.4 Integration test: Kafka gate fires on topic message during preset run
- [ ] 7.5 Integration test: Manual gate fires via `POST /api/gate/fire`
- [ ] 7.6 Integration test: Gate timeout aborts preset
- [ ] 7.7 Remove or rewrite tests for removed interactive gating functionality
