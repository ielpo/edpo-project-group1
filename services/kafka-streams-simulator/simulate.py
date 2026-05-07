"""
Simulator for the kafka-streams service.

Directly triggers block detection events (no distance sensor) and publishes
colour events, exercising the stream-stream join and inventory KTable.

Flow per block:
  1. Generate a UUID as the cubeId
  2. Publish a block-detected event to sensor.block-detected.v1 (keyed by cubeId)
  3. Wait ROBOT_ARM_DELAY_S (cube travels to the robot arm)
  4. Robot arm picks up the cube and presents it to the colour sensor
  5. Publish a colour event to sensor.color.raw.v1 (keyed by cubeId)
     → kafka-streams join resolves → inventory KTable updated
  6. Wait INVENTORY_DELAY_S (robot arm moves cube to inventory)

Usage:
  uv run simulate.py RED
  uv run simulate.py RED GREEN BLUE YELLOW
  uv run simulate.py --pause 10 RED GREEN BLUE
  uv run simulate.py --help
"""

import argparse
import json
import time
import uuid

from kafka import KafkaProducer

# ── Configuration ────────────────────────────────────────────────────────────

BOOTSTRAP = "localhost:9092"

TOPIC_COLOR          = "sensor.color.raw.v1"
TOPIC_BLOCK_DETECTED = "sensor.block-detected.v1"

SENSOR_UID          = "manual-trigger"
ROBOT_ARM_DELAY_S   = 2.0   # travel from conveyor to robot arm
COLOR_READINGS      = 10    # number of colour readings published per block (matches color-sensor-fake)
COLOR_INTERVAL_S    = 0.2   # interval between readings in seconds (matches color-sensor-fake)
INVENTORY_DELAY_S   = 2.0   # robot arm moves cube to inventory after colour detection
DEFAULT_PAUSE_S     = 5.0   # pause between blocks in a sequence

# RGB values that BlockColor.from() in the kafka-streams service will classify correctly
RGB = {
    "RED":    (220, 30,  30),
    "GREEN":  (30,  220, 30),
    "BLUE":   (30,  30,  220),
    "YELLOW": (220, 200, 20),
}

# ── Core simulation ──────────────────────────────────────────────────────────

def simulate_block(color: str, producer: KafkaProducer) -> None:
    """Simulate one block: trigger detection, then publish its colour."""

    print(f"\n{'─'*55}")
    print(f"  Block: {color}")
    print(f"{'─'*55}")

    cube_id = str(uuid.uuid4())

    # Step 1 — publish block-detected event (replaces physical distance sensor)
    block_event = json.dumps({
        "cubeId": cube_id,
        "sensorUid": SENSOR_UID,
        "timestamp": int(time.time() * 1000),
    }).encode()
    producer.send(TOPIC_BLOCK_DETECTED, key=cube_id.encode(), value=block_event)
    producer.flush()
    print(f"  [1/4] Block-detected published — cubeId: {cube_id}")

    # Step 2 — cube travels to robot arm
    print(f"  Waiting {ROBOT_ARM_DELAY_S}s (cube travelling to robot arm)...")
    time.sleep(ROBOT_ARM_DELAY_S)
    print(f"  [2/4] Robot arm picks up cube, presents to colour sensor")

    # Step 3 — colour sensor publishes multiple readings (matches color-sensor-fake behaviour)
    r, g, b = RGB[color]
    for i in range(COLOR_READINGS):
        color_event = json.dumps({"cubeId": cube_id, "r": r, "g": g, "b": b}).encode()
        producer.send(TOPIC_COLOR, key=cube_id.encode(), value=color_event)
        if i < COLOR_READINGS - 1:
            time.sleep(COLOR_INTERVAL_S)
    producer.flush()
    print(f"  [3/4] Colour published: {color} rgb=({r},{g},{b}) x{COLOR_READINGS} readings")

    # Step 4 — robot arm moves cube to inventory
    print(f"  Waiting {INVENTORY_DELAY_S}s (robot arm moving cube to inventory)...")
    time.sleep(INVENTORY_DELAY_S)
    print(f"  [4/4] Cube placed in inventory")

    print(f"\n  ✓ Done. Verify result:")
    print(f"    curl http://localhost:8104/inventory/{cube_id}")


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Simulate block detection events for the kafka-streams service.")
    parser.add_argument("colors", nargs="+", choices=list(RGB.keys()),
                        metavar="COLOR", help=f"One or more block colours: {list(RGB.keys())}")
    parser.add_argument("--pause", type=float, default=DEFAULT_PAUSE_S,
                        metavar="SECONDS", help=f"Pause between blocks in a sequence (default: {DEFAULT_PAUSE_S}s)")
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
