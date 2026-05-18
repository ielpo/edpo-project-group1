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

# Single block
uv run simulate.py RED

# Sequence of blocks
uv run simulate.py RED GREEN BLUE YELLOW

# Custom pause between blocks (default: 5 s)
uv run simulate.py --pause 10 RED GREEN
```

Available colours: `RED`, `GREEN`, `BLUE`, `YELLOW`

## Subscribe to inventory events

You can also open a lightweight console subscriber for the Kafka output topic:

```bash
cd services/kafka-streams-simulator

# Listen for new inventory events only
uv run consume_inventory_events.py

# Replay the full topic from the beginning
uv run consume_inventory_events.py --from-beginning

# Subscribe to a different topic if needed
uv run consume_inventory_events.py --topic sensor.block-detected.v1
```

By default the subscriber listens to `inventory.blocks.v1` on `localhost:9092` and
uses a random consumer group so you can start it on the fly without affecting other
consumers.

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
