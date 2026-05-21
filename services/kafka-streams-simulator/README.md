# kafka-streams-simulator

Python script that simulates the conveyor pipeline for the `kafka-streams` service — no physical hardware required.

## What it does

For each block colour specified on the command line:

1. Publishes a burst of distance readings to `sensor.distance.raw.v1` (simulates block under sensor)
2. Stops — the 2 s session window inactivity gap expires
3. Kafka Streams detects the session, generates a `cubeId`, and publishes to `sensor.block-detected.v1`
4. Publishes colour readings to `sensor.color.raw.v1` (no key, no cubeId)
5. Kafka Streams joins the block event with the first valid colour reading → inventory updated

## Usage

```bash
cd services/kafka-streams-simulator
uv run simulate.py
```

The script starts and prompts you to enter colours interactively.

**Available colours:** `RED`, `GREEN`, `BLUE`, `YELLOW`

Example interactive session:
```
Select a colour (or 'exit' to quit): RED
Placing one RED block
─────────────────────────────────────────────────────
  Block: RED
─────────────────────────────────────────────────────
[1/3] Distance burst published (10 readings, distance=10.0)
...
```

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Kafka on `localhost:9092`
- `kafka-streams` service running on `localhost:8104`

## Verify results

```bash
# Full inventory (cubeId assigned by Kafka Streams)
curl http://localhost:8104/inventory
```
