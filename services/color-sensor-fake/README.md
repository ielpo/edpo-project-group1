# Color Sensor Fake Service

Rust-based fake service that exposes random RGB values over HTTP.

## What it does

- Starts an HTTP server on port `8202`.
- Handles `GET /color` and returns JSON with random color values:

```json
{"r": 0, "g": 0, "b": 0}
```

## Configuration

- Bind address: `0.0.0.0`
- Port: `8202`
- Endpoint: `GET /color`

## Run locally

From this directory:

```bash
cargo run
```

## Run with Docker

From this directory:

```bash
docker build -t color-sensor-fake .
docker run -p 8202:8202 color-sensor-fake
```

## Fetch data

```bash
curl http://localhost:8202/color
```
