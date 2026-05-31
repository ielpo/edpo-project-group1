# Simulated Factory Service

Local development service that emulates selected factory hardware, exposes a browser UI,
and records a chronological event history for debugging end-to-end flows without the
physical setup.

## Features

- Deterministic presets such as `happy-path`, `wrong-color`, and `pickup-failure`
- REST endpoints compatible with the simulator contract consumed by `dobot-control`
- htmx-driven UI with server-rendered Jinja2 templates and Material Design 3 styling
- Server-Sent Events at `/sse/status` push out-of-band HTML fragments so panels live-update without page reloads
- In-memory event history for REST, MQTT, and simulator state transitions
- Color sensor and Dobot sensor endpoints, plus MQTT distance sensor publishing
- Health endpoint at `/health`
- **Plugin architecture for sensors** — each sensor type is an isolated Python module, registered in `config.yml` with a `type` field. Custom sensors can be added without modifying the engine. See [PLUGIN_DEVELOPMENT.md](PLUGIN_DEVELOPMENT.md).

## UI Architecture

The browser UI is composed of small server-rendered fragments instead of a JS
state machine:

```
templates/
├─ base.html                  page shell (Roboto, htmx, MD3 tokens)
└─ fragments/
   ├─ status.html             status badge
   ├─ presets.html            preset cards with run buttons
   ├─ twin.html              digital twin panel (sensors + inventory)
   ├─ events.html             chronological event list
   └─ pending.html            pending-action approve/reject cards
```

- `GET /` renders `base.html`. Each panel uses `hx-get="/fragments/{name}"`
  with `hx-trigger="load"` for the initial paint.
- `GET /sse/status` opens a `text/event-stream` connection. On every simulator
  event the server re-renders all panels as HTML fragments wrapped with
  `hx-swap-oob="true"` so htmx swaps them into the DOM by id.
- `PUT /api/config/sensors/{id}` always returns JSON with the updated sensor
  configuration. The HTMX twin form uses `hx-swap="none"` and relies on the
  SSE OOB stream for visual refresh.
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


Run the tests:

```bash
uv run pytest tests/
```

## Docker Compose

The development compose file includes the simulator and wires `dobot-control` to it:

```bash
docker compose -f docker-compose-development.yml up --build simulated-factory dobot-control mqtt
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SIMULATOR_CONFIG_PATH` | `config.yml` | Base YAML file containing presets and default sensors |
| `SIMULATOR_BIND` | `0.0.0.0` | Host/interface for the HTTP server |
| `SIMULATOR_PORT` | `8400` | HTTP port |
| `SIMULATOR_BROKER_URL` | unset | MQTT broker URL for distance publishes, for example `tcp://mqtt:1883` |
| `INVENTORY_URL` | `http://localhost:8103` | Base URL for inventory polling |
| `SIMULATED_FACTORY_KAFKA_OBSERVER` | (enabled) | Set to `false`/`0`/`off` to disable the Kafka observer |

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

- Runtime edits are in-memory only. Restart the service to return to the persisted defaults in `config.yml`.
- The Docker image defines a healthcheck against `/health`, so the endpoint can be reused for compose or Kubernetes readiness probes.

## Interactive Mode

The simulator supports an optional **interactive mode** that suspends selected Dobot
command batches until a human approves or rejects them through the UI or
`POST /api/interactive/{actionId}/resolve`. See [api.md](./api.md#interactive-mode)
for the full endpoint reference.

When enabling interactive mode, raise the HTTP timeout used by `dobot-control` above
the configured `timeoutSeconds` (default 30 s; recommended ≥ 35 s) so its requests do
not abort while waiting for the operator. Interactive mode is in-memory only and
resets on restart, so CI runs are unaffected.