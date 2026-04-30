## 1. Kafka Observer Integration

- [x] 1.1 Add Python Kafka client dependency to simulated-factory and verify environment lock/update succeeds.
- [x] 1.2 Implement a Kafka observer component that subscribes to `order.manufacture.v1`, `order.complete.v1`, `info.v1`, and `error.v1` using bootstrap `localhost:9092` and group `simulated-factory`.
- [x] 1.3 Wire observer startup and shutdown into FastAPI application lifecycle with non-fatal failure handling (service stays available if Kafka is down).
- [x] 1.4 Append consumed records into EventStore as `KAFKA` events containing topic and payload metadata.

## 2. Event Classification and Filtering

- [x] 2.1 Extend event retrieval logic to support explicit filter mode selection (`full` and `process`) while preserving existing pagination behavior.
- [x] 2.2 Define a centralized process event-type allowlist: `KAFKA`, `COMMAND`, `PENDING_ACTION`, `ACTION_RESOLVED`, `SENSOR_REQUEST`.
- [x] 2.3 Tag inbound color/IR sensor reads (`/api/dobot/{name}/color`, `/api/dobot/{name}/ir`) as `SENSOR_REQUEST` events.
- [x] 2.4 Ensure outgoing MQTT events continue to be recorded and remain visible in full mode only.

## 3. Events Panel UX Updates

- [x] 3.1 Add events-panel filter toggles for `Full log` and `Process view` in the htmx fragment/template.
- [x] 3.2 Implement process-mode rendering for command events as human-readable action summaries (move targets, suction state, conveyor actions).
- [x] 3.3 Keep raw payload inspection available for debugging in event cards.
- [x] 3.4 Ensure SSE-driven refresh preserves active filter mode and applies correct rendering rules.

## 4. API and Fragment Contract Alignment

- [x] 4.1 Update events fragment endpoint to accept and apply filter mode selection.
- [x] 4.2 Align `/api/events` filter semantics with UI filter toggles to avoid inconsistent results.
- [x] 4.3 Validate backward compatibility for callers that do not pass filter mode (default to full history behavior).

## 5. Tests and Verification

- [x] 5.1 Add unit/integration tests for EventStore/process filter selection and allowlist behavior.
- [x] 5.2 Add tests verifying `SENSOR_REQUEST` tagging for color/IR endpoints.
- [x] 5.3 Add tests (mocked Kafka consumer) confirming consumed topic messages are appended as `KAFKA` events.
- [x] 5.4 Add frontend/fragment tests for toggle behavior and human-readable command rendering.
- [x] 5.5 Execute manual smoke test: process view shows Kafka + command + sensor-request events, while full log still includes MQTT and other debug events.
