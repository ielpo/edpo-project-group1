# Simulated Factory Service

Local development service that emulates selected factory hardware, exposes a browser UI,
and records a chronological event history for debugging end-to-end flows without the
physical setup.

## Features

- Deterministic presets such as `happy-path`, `wrong-color`, and `pickup-failure`
- REST endpoints compatible with the simulator contract consumed by `dobot-control`
- htmx-driven UI with server-rendered Jinja2 templates and Material Design 3 styling
- Server-Sent Events at `/sse/status` push out-of-band HTML fragments so panels live-update without page reloads
- WebSocket live updates at `/ws/status` (kept for backend consumers; UI uses SSE)
- In-memory event history for REST, MQTT, and simulator state transitions
- Color sensor and Dobot sensor endpoints, plus MQTT distance sensor publishing
- Health endpoint at `/health`

## UI Architecture

The browser UI is composed of small server-rendered fragments instead of a JS
state machine:

```
templates/
├─ base.html                  page shell (Roboto, htmx, MD3 tokens)
└─ fragments/
   ├─ status.html             status badge
   ├─ presets.html            preset cards with run buttons
   ├─ sensors.html            sensor list (uses _sensor_card.html)
   ├─ _sensor_card.html       single sensor card with hx-put form
   ├─ events.html             chronological event list
   └─ pending.html            pending-action approve/reject cards
```

- `GET /` renders `base.html`. Each panel uses `hx-get="/fragments/{name}"`
  with `hx-trigger="load"` for the initial paint.
- `GET /sse/status` opens a `text/event-stream` connection. On every simulator
  event the server re-renders all panels as HTML fragments wrapped with
  `hx-swap-oob="true"` so htmx swaps them into the DOM by id.
- `PUT /api/config/sensors/{id}` returns an updated sensor card fragment when
  called with `HX-Request: true` and JSON otherwise, so direct API consumers
  are unaffected.
- htmx and the SSE / json-enc extensions are loaded from CDN; no Node build
  step is required. Roboto is loaded from Google Fonts.

## Development

Install dependencies:

```bash
cd services/simulated-factory
uv sync --group dev
```

Run the service locally:

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8400
```

Open the UI at `http://localhost:8400/`.

## Docker Compose

The development compose file includes the simulator and wires `dobot-control` to it:

```bash
docker compose -f docker-compose-development.yml up --build simulated-factory dobot-control mqtt
```

To use the OpenSpec override instead:

```bash
docker compose -f docker-compose.yml -f openspec/changes/add-simulated-factory-service/docker-compose.dev.yml up
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SIMULATOR_CONFIG_PATH` | `presets.yml` | Base YAML file containing presets and default sensors |
| `SIMULATOR_BIND` | `0.0.0.0` | Host/interface for the HTTP server |
| `SIMULATOR_PORT` | `8400` | HTTP port |
| `SIMULATOR_BROKER_URL` | unset | MQTT broker URL for distance publishes, for example `tcp://mqtt:1883` |
| `SIMULATOR_EVENT_BRIDGE` | `none` | Event bridge mode: `none`, `http`, or `kafka` |
| `SIMULATOR_EVENT_BRIDGE_URL` | unset | Target callback URL when `SIMULATOR_EVENT_BRIDGE=http` |
| `SIMULATOR_DISTANCE_TOPIC` | unset | Override the MQTT topic used by the distance sensor |

### Event Bridge Modes

- `none`: do not forward simulator events outside the process.
- `http`: POST event payloads to `SIMULATOR_EVENT_BRIDGE_URL`.
- `kafka`: reserve the event bridge for a Kafka-backed deployment. In this MVP the service logs
  the intent and still records the event locally so developer workflows remain deterministic.

## API Contract

The versioned simulator contract is documented in [api.md](./api.md). `DobotFake` in
`services/dobot-control` forwards commands to `/api/dobot/{name}/commands` and uses
`/api/dobot/{name}/color` and `/api/dobot/{name}/ir` for deterministic sensor reads.

## Running Presets

Start the happy path:

```bash
curl -X POST http://localhost:8400/api/presets/run \
  -H 'Content-Type: application/json' \
  -d '{"preset": "happy-path"}'
```

Inspect state:

```bash
curl http://localhost:8400/api/status
```

Force a failure by updating the color sensor:

```bash
curl -X PUT http://localhost:8400/api/config/sensors/color-left \
  -H 'Content-Type: application/json' \
  -d '{"mode": "fixed", "value": "BLUE", "raw_color": [0, 0, 1]}'
```

Note: The Factory Twin UI now exposes `scripted_values` and `raw_color` as individual form inputs; the API accepts arrays or legacy CSV strings for backward compatibility.

## Notes

- Runtime edits are in-memory only. Restart the service to return to the persisted defaults in `presets.yml`.
- The Docker image defines a healthcheck against `/health`, so the endpoint can be reused for compose or Kubernetes readiness probes.

## Developer notes — refactor (May 2026)

A small, low-risk refactor was applied to simplify shared logic and improve testability. Key changes:

- Extracted shared helper functions into `simulated_factory/utils.py` (color helpers, broker parsing, Kafka value decoding, path pattern regex).
- Refactored `simulated_factory/engine.py` to use the centralized helpers.
- Introduced a dependency factory in `simulated_factory/deps.py` and simplified `simulated_factory/api.py` wiring to call `build_dependencies()`.
- Moved MQTT broker URL parsing out of `distance_publisher` into `utils.parse_broker_target()`.
- Moved Kafka value decoding out of `kafka_observer` into `utils.decode_kafka_value()`.

### Files changed

- New:
  - `simulated_factory/utils.py`
  - `simulated_factory/deps.py`

- Edited:
  - `simulated_factory/api.py`
  - `simulated_factory/engine.py`
  - `simulated_factory/events.py`
  - `simulated_factory/models.py`
  - `simulated_factory/adapters/distance_publisher.py`
  - `simulated_factory/adapters/kafka_observer.py`

### Tests added

- `services/simulated-factory/tests/test_events_store.py`
- `services/simulated-factory/tests/test_api_wiring.py`
- `services/simulated-factory/tests/test_utils_kafka_key.py`
- `services/simulated-factory/tests/test_pending_action.py`

These tests were executed locally and validated the refactor; run them with:

```bash
PYTHONPATH=services/simulated-factory python -m pytest -q services/simulated-factory -q
```

These changes are internal-only and preserve public endpoints and behavior; unit and integration tests were run to validate the refactor.

Quick developer commands:

```bash
# Run just the simulated-factory test suite (from repo root)
PYTHONPATH=services/simulated-factory python -m pytest -q services/simulated-factory -q

# Run the service locally with the correct import path
PYTHONPATH=services/simulated-factory uv run uvicorn main:app --reload --host 0.0.0.0 --port 8400
```

Suggested next steps:

- When ready, open a changelist/PR that references `openspec/changes/refactor-backend-simplify` and this implementation summary.

## Interactive Mode

The simulator supports an optional **interactive mode** that suspends selected Dobot
command batches until a human approves or rejects them through the UI or
`POST /api/interactive/{actionId}/resolve`. See [api.md](./api.md#interactive-mode)
for the full endpoint reference.

When enabling interactive mode, raise the HTTP timeout used by `dobot-control` above
the configured `timeoutSeconds` (default 30 s; recommended ≥ 35 s) so its requests do
not abort while waiting for the operator. Interactive mode is in-memory only and
resets on restart, so CI runs are unaffected.