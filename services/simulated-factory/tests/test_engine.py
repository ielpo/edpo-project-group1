import asyncio
import logging
from pathlib import Path

import pytest

from simulated_factory.adapters.distance_publisher import DistancePublisher
from simulated_factory.engine import SimulationEngine
from simulated_factory.events import EventBridge, EventStore
from simulated_factory.models import SensorUpdateRequest


CONFIG_PATH = Path(__file__).resolve().parents[1] / "presets.yml"
LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_engine_runs_happy_path_deterministically() -> None:
    event_store = EventStore()
    engine = SimulationEngine(
        config_path=str(CONFIG_PATH),
        event_store=event_store,
        distance_publisher=DistancePublisher(None, event_store, LOGGER),
        event_bridge=EventBridge("none", None, LOGGER),
    )

    run_id = await engine.run_preset("happy-path")
    assert run_id == "run-0001"

    await asyncio.sleep(0.4)

    status = engine.get_status()
    assert status.status.value == "idle"
    assert status.currentPreset == "happy-path"
    assert status.currentStep == 4

    events, _ = event_store.list_events(page=1, page_size=20)
    assert any(item["type"] == "MQTT" for item in events)


@pytest.mark.asyncio
async def test_sensor_override_changes_runtime_value() -> None:
    event_store = EventStore()
    engine = SimulationEngine(
        config_path=str(CONFIG_PATH),
        event_store=event_store,
        distance_publisher=DistancePublisher(None, event_store, LOGGER),
        event_bridge=EventBridge("none", None, LOGGER),
    )

    sensor = await engine.update_sensor(
        "color-left",
        SensorUpdateRequest(mode="fixed", value="BLUE", raw_color=[0, 0, 1]),
    )

    assert sensor.value == "BLUE"
    assert engine.read_color("left") == ("BLUE", [0, 0, 1])
