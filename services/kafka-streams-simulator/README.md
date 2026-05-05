# kafka-streams-simulator

Python script that simulates block detection events for the `kafka-streams` service — no physical hardware required.

## What it does

For each block colour specified on the command line:

1. Generates a UUID as the `cubeId`
2. Publishes a block-detected event to `sensor.block-detected.v1` (keyed by `cubeId`)
3. Waits 2 s (simulates robot travel to the colour sensor)
4. Publishes a colour event to `sensor.color.raw.v1` (keyed by `cubeId`)

The kafka-streams service resolves the stream-stream join and updates the inventory KTable.

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

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Kafka on `localhost:9092`
- `kafka-streams` service running on `localhost:8104`

## Verify results

```bash
# Full inventory
curl http://localhost:8104/inventory

# Single block
curl http://localhost:8104/inventory/<cubeId>
```
