# Design: How to perform the backend refactor

## Principles

- Keep changes small and incremental.
- Preserve public API contracts; prefer additive changes.
- Tests first: add tests that capture current behavior before refactoring.
- Improve readability and reduce duplication.

## High-level approach

1. Audit and discover: run static analysis, grep for duplicates, list hotspots (high complexity, flaky tests, frequent changes).
2. Prioritize: pick a small, high-impact module or service to refactor first (one that has tests or where we can add tests easily).
3. Prepare safety net: add unit and integration tests that cover current behavior for the selected area.
4. Refactor in small steps: extract functions/classes, centralize shared utilities, and replace ad-hoc patterns with consistent abstractions.
5. Validate: run unit + integration tests, and a quick local integration smoke test.
6. Repeat: iterate across prioritized modules.

## Suggested refactor actions

- Extract shared utilities into a single `common` or `lib` package with clear public API.
- Replace duplicated serialization/deserialization logic with shared helpers.
- Centralize configuration handling and environment parsing.
- Standardize error types and logging format.
- Define and document stable service-to-service API interfaces; add contract tests where appropriate.
- Use dependency injection or clear factory functions to make side-effects testable.

## Testing strategy

- Add unit tests for extracted functions/classes.
- Add integration tests for service interactions (mock external dependencies where possible).
- Use test fixtures and small harnesses to simulate the minimal external systems.

## Migration and rollback

- Each logical change should be confined to a single PR and be revertable.
- Keep compatibility layers when changing public API; deprecate then remove in follow-up tasks.

## Notes on performance and observability

- Measure performance before and after major changes for hotspots.
- Ensure logs and metrics are preserved and enhanced where useful.

## Implementation summary (May 2, 2026)

The following is a concise summary of the concrete changes applied during
the first refactor iteration targeting `services/simulated-factory`.

- New files
	- `simulated_factory/utils.py` — central utility helpers (color helpers, path-pattern regex, MQTT broker parsing, Kafka value/key decoding, SSE formatter).
	- `simulated_factory/deps.py` — dependency factory: builds `EventStore`, `EventBridge`, `DistancePublisher`, `SimulationEngine`, and `KafkaObserver` for consistent wiring in `create_app()`.

- Modified files (key edits)
	- `simulated_factory/api.py` — simplified wiring via `build_dependencies()`, SSE formatting delegated to `utils.format_sse`.
	- `simulated_factory/engine.py` — centralized helpers usage, non-blocking event-bridge emission (scheduled via `asyncio.create_task`), and sensor-update helper extracted.
	- `simulated_factory/events.py` — `EventStore` improvements: subscriber queue sizing constant, `size()` and `clear()` helpers, small typing and doc additions.
	- `simulated_factory/models.py` — `PendingAction` helpers added (`wait_for_resolution`, `resolve`, `mark_timed_out`) to simplify test code and control flow.
	- `simulated_factory/adapters/distance_publisher.py` — payload construction extracted into `_build_payload()`; broker parsing delegated to `utils.parse_broker_target`.
	- `simulated_factory/adapters/kafka_observer.py` — Kafka key decoding extracted to `utils.decode_kafka_key`; value decoding uses `utils.decode_kafka_value`.

- Tests added
	- `services/simulated-factory/tests/test_events_store.py`
	- `services/simulated-factory/tests/test_api_wiring.py`
	- `services/simulated-factory/tests/test_utils_kafka_key.py`
	- `services/simulated-factory/tests/test_pending_action.py`

- Verification
	- The simulated-factory unit and integration-style tests were executed locally:

```bash
PYTHONPATH=services/simulated-factory python -m pytest -q services/simulated-factory -q
```

	- All tests passed on May 2, 2026.

- Notes
	- Changes are internal-only and preserve public HTTP/WebSocket/SSE endpoints.
	- Event bridge emission was made fire-and-forget to avoid blocking the simulation loop when external callbacks are slow.
	- The repository `openspec/changes/refactor-backend-simplify/tasks.md` records completed subtasks and remaining items; branch and PR creation is being handled manually by maintainers.

Next steps: finalize remaining module iterations, remove temporary compatibility shims when safe, and prepare a concise changelog for release notes.
