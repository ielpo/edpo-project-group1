## Context

The simulated-factory currently stores all runtime events in one in-memory event store and renders the same stream in the htmx events panel. This includes high-volume UI polling requests and preset step state transitions, which obscures process-level signals needed to follow Camunda-driven behavior. The change must preserve complete event retention for debugging while adding a process-focused operator view.

The same simulator should also observe Kafka process topics in parallel to the existing factory service, without becoming a command authority or changing factory-service behavior.

## Goals / Non-Goals

**Goals:**
- Keep a complete, queryable in-memory event history as the source of truth.
- Add a process-focused filtered events view for simulated-factory UI.
- Tag inbound sensor reads with a distinct event type so they are visible in process view.
- Consume process Kafka topics with fixed defaults (`localhost:9092`, consumer group `simulated-factory`) and append them into the local event store.
- Improve process-view readability for robot command events.
- Add UI toggles to switch between full and process-focused views.

**Non-Goals:**
- Replacing or modifying existing factory-service Kafka consumption.
- Removing existing REST/STATE/MQTT event recording.
- Building long-term event persistence beyond current in-memory retention.
- Introducing user-configurable Kafka bootstrap override in this change.

## Decisions

### 1) Keep one event store, add view-level filtering
Use the existing EventStore as complete log retention and add filtering at retrieval/render time.

Rationale:
- Preserves all debugging data.
- Avoids dual-write or split-store consistency issues.
- Minimizes migration risk because producers remain unchanged.

Alternatives considered:
- Write-time filtering: rejected because it loses debug visibility.
- Separate process-only store: rejected due to duplication and synchronization complexity.

### 2) Add explicit process event classification
Introduce explicit process categories for rendering/filtering:
- `KAFKA` (topic metadata and payload)
- `COMMAND`
- `PENDING_ACTION`
- `ACTION_RESOLVED`
- `SENSOR_REQUEST`

Rationale:
- Stable filter criteria independent of endpoint naming.
- Clear semantics for operator-facing panels.

Alternatives considered:
- Filter generic `REST` by path on every render: rejected as brittle and harder to evolve.

### 3) Observe Kafka topics as a passive parallel consumer
Add an async Kafka consumer component in simulated-factory that subscribes to:
- `order.manufacture.v1`
- `order.complete.v1`
- `info.v1`
- `error.v1`

Runtime defaults:
- bootstrap servers: `localhost:9092`
- group id: `simulated-factory`

The consumer only appends events to EventStore and never emits control commands.

Rationale:
- Enables end-to-end process visibility in simulator UI.
- Preserves existing service boundaries.

Alternatives considered:
- Mirror Kafka data via factory-service HTTP bridge: rejected due to additional hop and coupling.
- Reuse existing event bridge mode: rejected because this change requires topic-level observation in parallel.

### 4) Render process commands in human-readable form
In process mode, command payloads are summarized into action lines (for example, move targets and suction state) with optional raw payload disclosure.

Rationale:
- Improves operator comprehension of robot behavior.
- Keeps full payload available when needed.

Alternatives considered:
- JSON-only rendering: rejected as too noisy for process tracking.

### 5) Add explicit filter toggles in events panel
Add two toggles in the events panel:
- Full log
- Process view

Rationale:
- Fast operator switching without navigation.
- Keeps one panel and one mental model.

Alternatives considered:
- Separate pages/panels: rejected due to context switching overhead.

## Risks / Trade-offs

- [Kafka dependency introduces runtime failure modes] -> Mitigation: non-fatal startup with clear log warning and continued simulator operation without Kafka events.
- [Process filter may miss newly added event types later] -> Mitigation: centralize allowed process event-type set and cover with tests.
- [Human-readable command formatter can diverge from payload schema] -> Mitigation: fallback to raw payload when formatter cannot map a command shape.
- [High Kafka throughput can increase UI update volume] -> Mitigation: retain existing event cap and page-size limits; process view defaults to recent entries.

## Migration Plan

1. Add Kafka client dependency and new consumer module.
2. Start/stop consumer with FastAPI application lifecycle.
3. Append consumed Kafka messages as `KAFKA` events with topic and payload.
4. Tag inbound sensor read requests as `SENSOR_REQUEST` events.
5. Add process filter mode to events retrieval and fragment endpoint.
6. Update events template with full/process toggles and readable command rendering in process mode.
7. Add integration tests for Kafka ingestion pathway (mocked), filtering behavior, and rendering output.
8. Validate manual smoke flow: order topic event + command + sensor request visible in process view; MQTT visible only in full view.

Rollback strategy:
- Disable consumer startup path and revert event-panel filter controls while preserving full log behavior.

## Open Questions

- Should `info.v1` and `error.v1` always appear in process view, or only when `orderId`/`correlationId` is present?
- Should process-view toggles persist in browser local storage across reloads?
- Should `SENSOR_REQUEST` include only color/IR endpoint reads or any future sensor endpoint family under `/api/sensors/*`?
