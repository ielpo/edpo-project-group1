import asyncio
import logging
from pathlib import Path

import pytest

from simulated_factory.actuator_registry import ActuatorRegistry
from simulated_factory.adapters.mqtt_publisher import MqttPublisher
from simulated_factory.engine import SimulationEngine
from simulated_factory.events import EventStore
from simulated_factory.models import (
    AwaitTrigger,
    PresetDefinition,
    PresetStep,
    SensorUpdateRequest,
    TriggerEvent,
)
from simulated_factory.sensor_registry import SensorRegistry


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yml"
LOGGER = logging.getLogger(__name__)


def _make_engine() -> SimulationEngine:
    event_store = EventStore()
    mqtt = MqttPublisher(None, event_store, LOGGER)
    return SimulationEngine(
        event_store=event_store,
        mqtt_publisher=mqtt,
        sensor_registry=SensorRegistry(str(CONFIG_PATH), mqtt_publisher=mqtt),
        actuator_registry=ActuatorRegistry(),
    )


def _install_preset(engine: SimulationEngine, preset: PresetDefinition) -> None:
    engine.presets[preset.name] = preset


def _make_gated_preset(name: str = "gated") -> PresetDefinition:
    return PresetDefinition(
        name=name,
        steps=[
            PresetStep(
                name="wait-pickup",
                sensorUpdates={"color-left": "GREEN"},
                awaitTrigger=AwaitTrigger(
                    type="http",
                    method="POST",
                    path="/api/dobot/{name}/commands",
                    timeoutMs=10000,
                ),
            ),
            PresetStep(name="wrap-up", delayMs=10),
        ],
    )


async def _wait_for_gate(engine: SimulationEngine, iterations: int = 200) -> None:
    for _ in range(iterations):
        await asyncio.sleep(0.005)
        if engine.get_active_gate() is not None:
            return
    raise AssertionError("gate did not become active")


@pytest.mark.asyncio
async def test_engine_runs_happy_path_deterministically() -> None:
    engine = _make_engine()
    run_id = await engine.run_preset("happy-path")
    assert run_id == "run-0001"

    gate_events = [
        TriggerEvent(type="http", method="POST", path="/api/dobot/left/commands"),
        TriggerEvent(type="http", method="GET", path="/api/dobot/left/color"),
        TriggerEvent(type="http", method="POST", path="/api/dobot/left/commands"),
    ]
    for ev in gate_events:
        await _wait_for_gate(engine)
        assert engine.try_fire_gate(ev) is True

    await asyncio.wait_for(engine._run_task, timeout=2.0)

    status = engine.get_status()
    assert status.status.value == "idle"
    assert status.currentPreset == "happy-path"
    assert status.currentStep == 4
    assert status.activeGate is None


@pytest.mark.asyncio
async def test_sensor_override_changes_runtime_value() -> None:
    engine = _make_engine()
    sensor = await engine.update_sensor(
        "color-left",
        SensorUpdateRequest(value="BLUE", raw_color=[0, 0, 255]),
    )
    assert sensor.value == "BLUE"
    assert engine.read_color("left") == ("BLUE", [0, 0, 255])


@pytest.mark.asyncio
async def test_handle_actuator_commands_always_applies() -> None:
    engine = _make_engine()
    result = await engine.handle_actuator_commands(
        "left", {"type": "move", "target": {"x": 1, "y": 2, "z": 3, "r": 0}}
    )
    assert "correlationId" in result
    assert "outcome" not in result
    assert engine._actuator_registry.get_state("left").position.x == 1.0


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
async def test_sensor_updates_apply_immediately_before_gate() -> None:
    engine = _make_engine()
    _install_preset(engine, _make_gated_preset())
    await engine.run_preset("gated")
    await _wait_for_gate(engine)
    # Sensor update is applied as soon as the step begins, before the gate fires.
    assert engine._sensor_registry.live["color-left"]._cfg.value == "GREEN"


@pytest.mark.asyncio
async def test_http_gate_fires_on_matching_request() -> None:
    engine = _make_engine()
    _install_preset(engine, _make_gated_preset())
    await engine.run_preset("gated")
    await _wait_for_gate(engine)

    assert engine.get_status().activeGate is not None
    assert (
        engine.try_fire_gate(
            TriggerEvent(type="http", method="GET", path="/api/dobot/left/color")
        )
        is False
    )
    assert engine.get_active_gate() is not None
    assert (
        engine.try_fire_gate(
            TriggerEvent(type="http", method="POST", path="/api/dobot/left/commands")
        )
        is True
    )
    await asyncio.wait_for(engine._run_task, timeout=1.0)
    assert engine.get_status().activeGate is None


@pytest.mark.asyncio
async def test_kafka_gate_fires_on_matching_topic() -> None:
    engine = _make_engine()
    preset = PresetDefinition(
        name="kafka-gated",
        steps=[
            PresetStep(
                name="await-msg",
                awaitTrigger=AwaitTrigger(
                    type="kafka", topic="orders.created", timeoutMs=10000
                ),
            )
        ],
    )
    _install_preset(engine, preset)
    await engine.run_preset("kafka-gated")
    await _wait_for_gate(engine)

    assert engine.try_fire_gate(TriggerEvent(type="kafka", topic="other")) is False
    assert (
        engine.try_fire_gate(TriggerEvent(type="kafka", topic="orders.created"))
        is True
    )
    await asyncio.wait_for(engine._run_task, timeout=1.0)


@pytest.mark.asyncio
async def test_manual_gate_fires_unconditionally() -> None:
    engine = _make_engine()
    preset = PresetDefinition(
        name="manual-gated",
        steps=[
            PresetStep(
                name="await-operator",
                awaitTrigger=AwaitTrigger(type="manual", timeoutMs=10000),
            )
        ],
    )
    _install_preset(engine, preset)
    await engine.run_preset("manual-gated")
    await _wait_for_gate(engine)

    assert engine.try_fire_gate(TriggerEvent(type="manual")) is True
    await asyncio.wait_for(engine._run_task, timeout=1.0)
    assert engine.get_status().status.value == "idle"


@pytest.mark.asyncio
async def test_manual_gate_reject_aborts_preset() -> None:
    engine = _make_engine()
    preset = PresetDefinition(
        name="manual-reject",
        steps=[
            PresetStep(
                name="await-operator",
                awaitTrigger=AwaitTrigger(type="manual", timeoutMs=10000),
            ),
            PresetStep(name="should-not-run", delayMs=10),
        ],
    )
    _install_preset(engine, preset)
    await engine.run_preset("manual-reject")
    await _wait_for_gate(engine)

    assert engine.reject_active_gate() is True
    await asyncio.wait_for(engine._run_task, timeout=1.0)
    # Preset aborted at first step.
    assert engine.get_status().currentStep == 1


@pytest.mark.asyncio
async def test_reject_only_works_for_manual_gates() -> None:
    engine = _make_engine()
    _install_preset(engine, _make_gated_preset())
    await engine.run_preset("gated")
    await _wait_for_gate(engine)
    assert engine.reject_active_gate() is False
    # Clean up by firing.
    engine.try_fire_gate(
        TriggerEvent(type="http", method="POST", path="/api/dobot/left/commands")
    )
    await asyncio.wait_for(engine._run_task, timeout=1.0)


@pytest.mark.asyncio
async def test_gate_timeout_aborts_preset() -> None:
    engine = _make_engine()
    preset = PresetDefinition(
        name="quick-timeout",
        steps=[
            PresetStep(
                name="will-timeout",
                sensorUpdates={"color-left": "BLUE"},
                awaitTrigger=AwaitTrigger(
                    type="http",
                    method="POST",
                    path="/api/dobot/{name}/commands",
                    timeoutMs=50,
                ),
            ),
            PresetStep(name="should-not-run", delayMs=10),
        ],
    )
    _install_preset(engine, preset)
    await engine.run_preset("quick-timeout")
    await asyncio.wait_for(engine._run_task, timeout=2.0)
    # Side-effects applied before gate even though timed out.
    assert engine._sensor_registry.live["color-left"]._cfg.value == "BLUE"
    # Preset aborted at first step.
    assert engine.get_status().currentStep == 1


@pytest.mark.asyncio
async def test_stop_clears_active_gate() -> None:
    engine = _make_engine()
    _install_preset(engine, _make_gated_preset())
    await engine.run_preset("gated")
    await _wait_for_gate(engine)
    await engine.stop()
    await asyncio.wait_for(engine._run_task, timeout=1.0)
    assert engine.get_active_gate() is None
    assert engine.get_status().activeGate is None


@pytest.mark.asyncio
async def test_reset_while_gated_clears_without_hanging() -> None:
    engine = _make_engine()
    _install_preset(engine, _make_gated_preset())
    await engine.run_preset("gated")
    await _wait_for_gate(engine)
    await asyncio.wait_for(engine.reset(), timeout=2.0)
    assert engine.get_active_gate() is None
    assert engine.get_status().activeGate is None
    assert engine.get_status().status.value == "idle"


@pytest.mark.asyncio
async def test_status_active_gate_lifecycle() -> None:
    engine = _make_engine()
    _install_preset(engine, _make_gated_preset())
    assert engine.get_status().activeGate is None

    await engine.run_preset("gated")
    await _wait_for_gate(engine)

    gate = engine.get_status().activeGate
    assert gate is not None
    assert gate.type == "http"
    assert gate.method == "POST"
    assert gate.path == "/api/dobot/{name}/commands"

    engine.try_fire_gate(
        TriggerEvent(type="http", method="POST", path="/api/dobot/left/commands")
    )
    await asyncio.wait_for(engine._run_task, timeout=1.0)
    assert engine.get_status().activeGate is None


@pytest.mark.asyncio
async def test_pending_action_snapshot_during_gate() -> None:
    engine = _make_engine()
    _install_preset(engine, _make_gated_preset())
    await engine.run_preset("gated")
    await _wait_for_gate(engine)

    pending = engine.get_pending_actions()
    assert len(pending) == 1
    action = pending[0]
    assert action["stepName"] == "wait-pickup"
    assert action["triggerType"] == "http"
    assert action["triggerSpec"]["method"] == "POST"
    assert action["triggerSpec"]["path"] == "/api/dobot/{name}/commands"
    assert action["timeoutMs"] == 10000

    engine.try_fire_gate(
        TriggerEvent(type="http", method="POST", path="/api/dobot/left/commands")
    )
    await asyncio.wait_for(engine._run_task, timeout=1.0)
    assert engine.get_pending_actions() == []
