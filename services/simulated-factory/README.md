# Simulated Factory Service

Local development service that emulates selected factory hardware, exposes a browser UI,
and records a chronological event history for debugging end-to-end flows without the
physical setup.

## Features

- Deterministic presets such as `happy-path`, `wrong-color`, and `pickup-failure`
- REST endpoints compatible with the simulator contract consumed by `dobot-control`
- WebSocket live updates at `/ws/status`
- In-memory event history for REST, MQTT, and simulator state transitions
- Color sensor and Dobot sensor endpoints, plus MQTT distance sensor publishing
- Health endpoint at `/health`

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

## Notes

- Runtime edits are in-memory only. Restart the service to return to the persisted defaults in `presets.yml`.
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