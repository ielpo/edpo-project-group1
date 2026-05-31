"""
Simulator for the kafka-streams service.

Simulates the physical conveyor pipeline without hardware:
  1. Continuously publishes distance readings at 1s intervals
  2. User selects a color via CLI input
  3. Switches to publishing that color's readings at 1s intervals
  4. Returns to distance readings after user makes next selection

Usage:
  uv run simulate.py
"""

import json
import threading
import time

from kafka import KafkaProducer

# ── Configuration ────────────────────────────────────────────────────────────

BOOTSTRAP = "localhost:9092"

TOPIC_DISTANCE = "sensor.distance.raw.v1"
TOPIC_COLOR    = "sensor.color.raw.v1"

PUBLISH_INTERVAL_S = 1      # publish every 1 second (both distance and color)

DISTANCE_BLOCK     = 10.0   # cm
DISTANCE_FREE      = 30.0   # cm
DISTANCE_READINGS  = 10     # number of readings in the burst

BLOCK_INACTIVITY_GAP_S = 3.0               # matches BlockColorTopology wall-clock inactivity gap
DETECTION_WAIT_S = BLOCK_INACTIVITY_GAP_S + 0.5

COLOR_READINGS    = 5      # number of colour readings published per block
DEFAULT_PAUSE_S = 5.0       # pause between blocks in a sequence


# RGB values that BlockColor.from() will classify correctly
RGB = {
    "RED":    (220, 30,  30),
    "GREEN":  (30,  220, 30),
    "BLUE":   (30,  30,  220),
    "YELLOW": (220, 200, 20),
    "INVALID": (0, 0, 0),
}

# ── Core simulation ──────────────────────────────────────────────────────────

class SimulationState:
    """Thread-safe state holder for the current publishing mode."""
    def __init__(self):
        self.lock = threading.Lock()
        self.current_color: str | None = "INVALID"
        self.current_distance: float | None  = 30

    def set_color(self, color):
        with self.lock:
            self.current_color = color

    def get_color(self):
        with self.lock:
            return self.current_color
        
    def set_distance(self, distance):
        with self.lock:
            self.current_distance = distance

    def get_distance(self):
        with self.lock:
            return self.current_distance


def publish_loop(producer: KafkaProducer, state: SimulationState) -> None:
    """Continuously publish distance and color readings based on state."""
    try:
        while True:
            color = state.get_color()
            distance = state.get_distance()
            
            if distance != None:
                # Publish distance reading
                event = json.dumps({
                    "distance": distance,
                    "timestamp": int(time.time() * 1000),
                }).encode()
                producer.send(TOPIC_DISTANCE, key=None, value=event)
                producer.flush()
                #print(f"  → Distance: {distance} cm")
                
            if color != None:
                # Publish color reading
                r, g, b = RGB[color]
                event = json.dumps({"r": r, "g": g, "b": b}).encode()
                producer.send(TOPIC_COLOR, key=None, value=event)
                producer.flush()
                # print(f"  → Colour ({color}): rgb=({r},{g},{b})")
            
            time.sleep(PUBLISH_INTERVAL_S)
            
    except KeyboardInterrupt:
        pass


def simulate_block(color: str, state: SimulationState) -> None:
    """Simulate one block passing through the conveyor pipeline."""

    print(f"\n{'─'*55}")
    print(f"  Block: {color}")
    print(f"{'─'*55}")

    # Step 1 — publish distance readings (block under sensor)
    
    state.set_distance(DISTANCE_BLOCK)
    time.sleep(DISTANCE_READINGS * PUBLISH_INTERVAL_S)
    state.set_distance(DISTANCE_FREE)

    print(f"  [1/3] Distance burst published ({DISTANCE_READINGS} readings, distance={DISTANCE_BLOCK})")

    # Step 2 — wait for the wall-clock inactivity gap to elapse and Kafka Streams to process it
    print(f"  Waiting {DETECTION_WAIT_S}s for wall-clock inactivity detection...")
    time.sleep(DETECTION_WAIT_S)
    print(f"  [2/3] Inactivity detected — Kafka Streams has generated a cubeId")

    # Step 3 — publish colour readings (no key, no cubeId — Kafka Streams joins by time)
    state.set_color(color)
    time.sleep(COLOR_READINGS * PUBLISH_INTERVAL_S)
    state.set_color("INVALID")

    r, g, b = RGB[color]
    print(f"  [3/3] Colour published: {color} rgb=({r},{g},{b}) x{COLOR_READINGS} readings")

    print(f"\n  ✓ Done. Kafka Streams joins block + colour and updates inventory.")
    print(f"    curl http://localhost:8104/inventory")

# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    producer = KafkaProducer(bootstrap_servers=BOOTSTRAP)
    state = SimulationState()

    print(f"Kafka: {BOOTSTRAP}")
    print(f"Available colours: {list(RGB.keys())}")

    # Start publishing thread
    publisher = threading.Thread(target=publish_loop, args=(producer, state), daemon=True)
    publisher.start()
    print("\nContinuous publishing started")
    print("Type a color to 'place' a block, or 'exit'/'quit' to stop.\n")

    try:
        while True:
            color_input = input("Select a colour (or 'exit' to quit): ").strip().upper()
            
            if color_input in ("EXIT", "QUIT"):
                print("\nStopping simulation...")
                break
            
            if color_input not in RGB:
                print(f"Invalid color. Please choose from: {list(RGB.keys())}")
                continue
            
            print(f"Placing one {color_input} block")
            simulate_block(color_input, state)
            
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted.")

    finally:
        producer.close()
        print("Simulation complete.")
        print("Full inventory: curl http://localhost:8104/inventory")


if __name__ == "__main__":
    main()
