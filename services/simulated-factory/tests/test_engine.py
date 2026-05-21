import asyncio
import logging
from pathlib import Path

import pytest

from simulated_factory.adapters.distance_publisher import DistancePublisher
from simulated_factory.engine import SimulationEngine
from simulated_factory.events import EventBridge, EventStore
from simulated_factory.models import InteractiveConfig, SensorUpdateRequest


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


def _make_engine() -> SimulationEngine:
    event_store = EventStore()
    return SimulationEngine(
        config_path=str(CONFIG_PATH),
        event_store=event_store,
        distance_publisher=DistancePublisher(None, event_store, LOGGER),
        event_bridge=EventBridge("none", None, LOGGER),
    )


@pytest.mark.asyncio
async def test_handle_dobot_commands_auto_resolves_when_not_intercepted() -> None:
    engine = _make_engine()
    result = await engine.handle_dobot_commands(
        "left", {"type": "move", "target": {"x": 1, "y": 2, "z": 3, "r": 0}}
    )
    assert "correlationId" in result
    assert "outcome" not in result
    assert engine.get_pending_actions() == []
    assert engine.state.dobots["left"].position.x == 1.0


@pytest.mark.asyncio
async def test_handle_dobot_commands_suspends_until_resolved() -> None:
    engine = _make_engine()
    engine.set_interactive_config(
        InteractiveConfig(intercepted={"move"}, timeout_seconds=5)
    )

    task = asyncio.create_task(
        engine.handle_dobot_commands(
            "left", {"type": "move", "target": {"x": 7, "y": 0, "z": 0, "r": 0}}
        )
    )
    # Wait for the action to be queued.
    for _ in range(50):
        await asyncio.sleep(0.01)
        if engine.get_pending_actions():
            break
    pending = engine.get_pending_actions()
    assert len(pending) == 1
    assert not task.done()

    action_id = pending[0]["id"]
    await engine.resolve_action(action_id, "success")

    result = await asyncio.wait_for(task, timeout=1.0)
    assert result["outcome"] == "success"
    assert "timedOut" not in result
    assert engine.get_pending_actions() == []
    assert engine.state.dobots["left"].position.x == 7.0


@pytest.mark.asyncio
async def test_handle_dobot_commands_times_out() -> None:
    engine = _make_engine()
    engine.set_interactive_config(
        InteractiveConfig(intercepted={"move"}, timeout_seconds=1)
    )
    # Bypass the >=1 second wait by patching the configured timeout via wait_for short-circuit.
    # We rely on the minimum-1-second timeout but accelerate using a direct override.
    engine.interactive_config = InteractiveConfig(
        intercepted={"move"}, timeout_seconds=1
    )

    result = await engine.handle_dobot_commands(
        "left", {"type": "move", "target": {"x": 9, "y": 0, "z": 0, "r": 0}}
    )
    assert result["outcome"] == "failure"
    assert result.get("timedOut") is True
    assert engine.get_pending_actions() == []
    # State should NOT have been applied for failed actions.
    assert engine.state.dobots["left"].position.x == 0.0


@pytest.mark.asyncio
async def test_resolve_unknown_action_raises_key_error() -> None:
    engine = _make_engine()
    with pytest.raises(KeyError):
        await engine.resolve_action("act-9999", "success")
