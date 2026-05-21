## Why

The simulated-factory event panel is too noisy to follow Camunda-relevant process flow during demos and debugging. We need a process-focused view that highlights order lifecycle, robot actions, and sensor requests while preserving full logs for deep troubleshooting.

## What Changes

- Add a process-focused event view in simulated-factory that filters displayed events to Camunda-relevant signals.
- Keep complete in-memory event history unchanged and always available for debugging.
- Add Kafka consumption in simulated-factory (observer mode) for process topics (`order.manufacture.v1`, `order.complete.v1`, `info.v1`, `error.v1`) using consumer group `simulated-factory` and bootstrap `localhost:9092`.
- Introduce distinct sensor-request event tagging for inbound sensor reads so these events are visible in the process-focused view.
- Add UI filter toggles in the events panel to switch between full and process-focused logs.
- Improve rendering of robot command events in process-focused mode to human-readable actions (for example, move targets and suction state) rather than only raw JSON blocks.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `simulated-factory-service`: Extend event ingestion and classification with Kafka observer consumption and sensor-request tagging while preserving full event history.
- `simulator-htmx-frontend`: Add event-panel filter toggles and process-focused, human-readable command rendering.

## Impact

- Affected code: `services/simulated-factory/simulated_factory/api.py`, `services/simulated-factory/simulated_factory/events.py`, `services/simulated-factory/simulated_factory/engine.py`, new Kafka consumer integration module(s), and events templates in `services/simulated-factory/templates/fragments/`.
- API/UI behavior: event-panel filtering behavior and event rendering semantics change in the simulator UI.
- Dependencies: add Python Kafka client dependency.
- Runtime/system: simulated-factory opens an additional Kafka consumer in parallel to existing factory-service consumption.
