"""
Simulator for the kafka-streams service.

Simulates the physical conveyor pipeline without hardware:
  1. Publishes a burst of distance readings (block under the sensor)
  2. Stops — the 2 s session window inactivity gap expires
  3. Kafka Streams detects the session, generates a cubeId, publishes to sensor.block-detected.v1
  4. Publishes colour readings — Kafka Streams joins them with the block event
  5. Inventory KTable is updated with the first valid colour

Usage:
  uv run simulate.py RED
  uv run simulate.py RED GREEN BLUE YELLOW
  uv run simulate.py --pause 10 RED GREEN BLUE
  uv run simulate.py --help
"""

import argparse
import json
import time

from kafka import KafkaProducer

# ── Configuration ────────────────────────────────────────────────────────────

BOOTSTRAP = "localhost:9092"

TOPIC_DISTANCE = "sensor.distance.raw.v1"
TOPIC_COLOR    = "sensor.color.raw.v1"

DISTANCE_VALUE     = 10.0   # cm — well below the 25.0 threshold
DISTANCE_READINGS  = 10     # number of readings in the burst
DISTANCE_INTERVAL_S = 0.1   # interval between distance readings

SESSION_GAP_S  = 2.0        # must match TopologyConfig inactivity gap
SESSION_WAIT_S = 3.5        # wait after burst: session gap + processing buffer

COLOR_READINGS    = 10      # number of colour readings published per block
COLOR_INTERVAL_S  = 0.2     # interval between colour readings

DEFAULT_PAUSE_S = 5.0       # pause between blocks in a sequence

# RGB values that BlockColor.from() will classify correctly
RGB = {
    "RED":    (220, 30,  30),
    "GREEN":  (30,  220, 30),
    "BLUE":   (30,  30,  220),
    "YELLOW": (220, 200, 20),
}

# ── Core simulation ──────────────────────────────────────────────────────────

def simulate_block(color: str, producer: KafkaProducer) -> None:
    """Simulate one block passing through the conveyor pipeline."""

    print(f"\n{'─'*55}")
    print(f"  Block: {color}")
    print(f"{'─'*55}")

    # Step 1 — publish distance readings (block under sensor)
    for i in range(DISTANCE_READINGS):
        event = json.dumps({
            "distance": DISTANCE_VALUE,
            "timestamp": int(time.time() * 1000),
        }).encode()
        producer.send(TOPIC_DISTANCE, key=None, value=event)
        if i < DISTANCE_READINGS - 1:
            time.sleep(DISTANCE_INTERVAL_S)
    producer.flush()
    print(f"  [1/3] Distance burst published ({DISTANCE_READINGS} readings, distance={DISTANCE_VALUE})")

    # Step 2 — wait for session window to close and Kafka Streams to process
    print(f"  Waiting {SESSION_WAIT_S}s for session window to close...")
    time.sleep(SESSION_WAIT_S)
    print(f"  [2/3] Session closed — Kafka Streams has generated a cubeId")

    # Step 3 — publish colour readings (no key, no cubeId — Kafka Streams joins by time)
    r, g, b = RGB[color]
    for i in range(COLOR_READINGS):
        event = json.dumps({"r": r, "g": g, "b": b}).encode()
        producer.send(TOPIC_COLOR, key=None, value=event)
        if i < COLOR_READINGS - 1:
            time.sleep(COLOR_INTERVAL_S)
    producer.flush()
    print(f"  [3/3] Colour published: {color} rgb=({r},{g},{b}) x{COLOR_READINGS} readings")

    print(f"\n  ✓ Done. Kafka Streams joins block + colour and updates inventory.")
    print(f"    curl http://localhost:8104/inventory")


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Simulate block detection for the kafka-streams service.")
    parser.add_argument("colors", nargs="+", choices=list(RGB.keys()),
                        metavar="COLOR", help=f"One or more block colours: {list(RGB.keys())}")
    parser.add_argument("--pause", type=float, default=DEFAULT_PAUSE_S,
                        metavar="SECONDS", help=f"Pause between blocks (default: {DEFAULT_PAUSE_S}s)")
    args = parser.parse_args()

    producer = KafkaProducer(bootstrap_servers=BOOTSTRAP)

    print(f"Kafka: {BOOTSTRAP}")
    print(f"Blocks to simulate: {args.colors}")

    for i, color in enumerate(args.colors):
        simulate_block(color, producer)
        if i < len(args.colors) - 1:
            print(f"\n  Pausing {args.pause}s before next block...")
            time.sleep(args.pause)

    producer.close()
    print("\nSimulation complete.")
    print("Full inventory: curl http://localhost:8104/inventory")


if __name__ == "__main__":
    main()
