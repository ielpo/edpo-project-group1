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

    # happy-path now contains gated steps; drive them by simulating the
    # incoming requests Camunda would issue.
    gate_calls = [
        ("POST", "/api/dobot/left/commands"),  # pickup
        ("GET", "/api/dobot/left/color"),       # color-check
        ("POST", "/api/dobot/left/commands"),  # place
    ]
    for method, path in gate_calls:
        for _ in range(200):
            await asyncio.sleep(0.01)
            if engine._step_gate is not None:
                break
        assert engine.fire_gate_if_matches(method, path) is True

    await asyncio.wait_for(engine._run_task, timeout=2.0)

    status = engine.get_status()
    assert status.status.value == "idle"
    assert status.currentPreset == "happy-path"
    assert status.currentStep == 4
    assert status.waitingForRequest is None

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


# ---------------------------------------------------------------------------
# Request-driven preset gate tests
# ---------------------------------------------------------------------------

from simulated_factory.models import (  # noqa: E402
    AwaitRequest,
    PresetDefinition,
    PresetStep,
)


def _make_gated_preset(name: str = "gated") -> PresetDefinition:
    return PresetDefinition(
        name=name,
        steps=[
            PresetStep(
                name="wait-pickup",
                delayMs=10000,
                sensorUpdates={"color-left": "GREEN"},
                awaitRequest=AwaitRequest(
                    method="POST", path="/api/dobot/{name}/commands"
                ),
            ),
            PresetStep(name="wrap-up", delayMs=10),
        ],
    )


def _install_preset(engine: SimulationEngine, preset: PresetDefinition) -> None:
    engine.presets[preset.name] = preset


@pytest.mark.asyncio
async def test_non_gated_step_advances_on_timer() -> None:
    engine = _make_engine()
    preset = PresetDefinition(
        name="plain",
        steps=[PresetStep(name="only", delayMs=20)],
    )
    _install_preset(engine, preset)
    await engine.run_preset("plain")
    await asyncio.wait_for(engine._run_task, timeout=1.0)
    assert engine.get_status().status.value == "idle"
    assert engine.get_status().currentStep == 1


@pytest.mark.asyncio
async def test_gated_step_holds_until_fire_gate_matches() -> None:
    engine = _make_engine()
    _install_preset(engine, _make_gated_preset())
    await engine.run_preset("gated")

    # Wait until the gate is installed.
    for _ in range(200):
        await asyncio.sleep(0.005)
        if engine._step_gate is not None:
            break
    assert engine._step_gate is not None
    assert engine.get_status().waitingForRequest is not None
    assert engine.sensors["color-left"].value == "RED"  # not applied yet

    # Non-matching request does not fire.
    assert engine.fire_gate_if_matches("GET", "/api/dobot/left/color") is False
    assert engine._step_gate is not None

    # Matching request fires; side-effects applied synchronously.
    assert engine.fire_gate_if_matches("POST", "/api/dobot/left/commands") is True
    assert engine.sensors["color-left"].value == "GREEN"

    await asyncio.wait_for(engine._run_task, timeout=1.0)
    assert engine.get_status().waitingForRequest is None
    assert engine.get_status().currentStep == 2


@pytest.mark.asyncio
async def test_gated_step_times_out_emits_event() -> None:
    engine = _make_engine()
    preset = PresetDefinition(
        name="gated-fast",
        steps=[
            PresetStep(
                name="will-timeout",
                delayMs=50,
                sensorUpdates={"color-left": "BLUE"},
                awaitRequest=AwaitRequest(
                    method="POST", path="/api/dobot/{name}/commands"
                ),
            ),
        ],
    )
    _install_preset(engine, preset)
    await engine.run_preset("gated-fast")
    await asyncio.wait_for(engine._run_task, timeout=2.0)

    # Side-effects applied on timeout.
    assert engine.sensors["color-left"].value == "BLUE"

    events, _ = engine.event_store.list_events(page=1, page_size=50)
    assert any(
        ev.get("payload", {}).get("gateTimedOut") is True for ev in events
    ), events


@pytest.mark.asyncio
async def test_stop_clears_active_gate() -> None:
    engine = _make_engine()
    _install_preset(engine, _make_gated_preset())
    await engine.run_preset("gated")
    for _ in range(200):
        await asyncio.sleep(0.005)
        if engine._step_gate is not None:
            break
    assert engine._step_gate is not None

    await engine.stop()
    await asyncio.wait_for(engine._run_task, timeout=1.0)
    assert engine._step_gate is None
    assert engine.get_status().waitingForRequest is None


@pytest.mark.asyncio
async def test_reset_while_gated_clears_without_hanging() -> None:
    engine = _make_engine()
    _install_preset(engine, _make_gated_preset())
    await engine.run_preset("gated")
    for _ in range(200):
        await asyncio.sleep(0.005)
        if engine._step_gate is not None:
            break
    assert engine._step_gate is not None

    await asyncio.wait_for(engine.reset(), timeout=2.0)
    assert engine._step_gate is None
    assert engine.get_status().waitingForRequest is None
    assert engine.get_status().status.value == "idle"


def test_matches_gate_handles_name_wildcard() -> None:
    engine = _make_engine()
    step = PresetStep(
        name="x",
        delayMs=10,
        awaitRequest=AwaitRequest(
            method="POST", path="/api/dobot/{name}/commands"
        ),
    )
    engine._step_gate = (step.awaitRequest, asyncio.Event(), step)

    assert engine._matches_gate("POST", "/api/dobot/left/commands") is True
    assert engine._matches_gate("POST", "/api/dobot/right/commands") is True
    assert engine._matches_gate("POST", "/api/dobot/left/commands/extra") is False
    assert engine._matches_gate("GET", "/api/dobot/left/commands") is False
    assert engine._matches_gate("POST", "/api/dobot//commands") is False


@pytest.mark.asyncio
async def test_status_waiting_for_request_lifecycle() -> None:
    engine = _make_engine()
    _install_preset(engine, _make_gated_preset())
    assert engine.get_status().waitingForRequest is None

    await engine.run_preset("gated")
    for _ in range(200):
        await asyncio.sleep(0.005)
        if engine.get_status().waitingForRequest is not None:
            break

    waiting = engine.get_status().waitingForRequest
    assert waiting is not None
    assert waiting.method == "POST"
    assert waiting.path == "/api/dobot/{name}/commands"

    engine.fire_gate_if_matches("POST", "/api/dobot/left/commands")
    await asyncio.wait_for(engine._run_task, timeout=1.0)
    assert engine.get_status().waitingForRequest is None

