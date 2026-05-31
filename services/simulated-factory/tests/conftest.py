"""Pytest configuration for simulated-factory.

Disables the Kafka observer by default during tests so the FastAPI lifespan
does not attempt a real Kafka connection. Tests that need the observer
behavior should construct it directly with explicit fakes.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("SIMULATED_FACTORY_KAFKA_OBSERVER", "disabled")
