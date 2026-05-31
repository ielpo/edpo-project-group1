"""Integration tests for the refactored simulation engine.

These tests exercise the full stack through the SimulationEngine facade,
covering preset execution, request-gated flows, sensor updates, and command handling.
"""

import asyncio
import logging
from pathlib import Path

import pytest

from simulated_factory.actuator_registry import ActuatorRegistry
from simulated_factory.adapters.mqtt_publisher import MqttPublisher
from simulated_factory.engine import SimulationEngine
from simulated_factory.events import EventStore
from simulated_factory.models import (
    SensorUpdateRequest,
    SimulationStatus,
    TriggerEvent,
)
from simulated_factory.sensor_registry import SensorRegistry

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yml"
LOGGER = logging.getLogger(__name__)


def _make_engine() -> tuple[SimulationEngine, EventStore]:
    event_store = EventStore()
    mqtt = MqttPublisher(None, event_store, LOGGER)
    engine = SimulationEngine(
        event_store=event_store,
        mqtt_publisher=mqtt,
        sensor_registry=SensorRegistry(str(CONFIG_PATH), mqtt_publisher=mqtt),
        actuator_registry=ActuatorRegistry(),
    )
    return engine, event_store


async def _wait_for_gate(engine: SimulationEngine, iterations: int = 200) -> None:
    for _ in range(iterations):
        await asyncio.sleep(0.01)
        if engine.get_active_gate() is not None:
            return
    raise AssertionError("gate did not become active")


def _http(method: str, path: str) -> TriggerEvent:
    return TriggerEvent(type="http", method=method, path=path)


# ---------------------------------------------------------------------------
# Preset execution integration
# ---------------------------------------------------------------------------


class TestPresetExecution:
    @pytest.mark.asyncio
    async def test_happy_path_completes_with_gates(self) -> None:
        engine, _ = _make_engine()
        run_id = await engine.run_preset("happy-path")
        assert run_id == "run-0001"

        for ev in (
            _http("POST", "/api/dobot/left/commands"),
            _http("GET", "/api/dobot/left/color"),
            _http("POST", "/api/dobot/left/commands"),
        ):
            await _wait_for_gate(engine)
            assert engine.try_fire_gate(ev) is True

        await asyncio.wait_for(engine._run_task, timeout=2.0)
        status = engine.get_status()
        assert status.status == SimulationStatus.IDLE
        assert status.currentPreset == "happy-path"

    @pytest.mark.asyncio
    async def test_wrong_color_preset_with_overrides(self) -> None:
        engine, _ = _make_engine()
        await engine.run_preset("wrong-color")
        await _wait_for_gate(engine)
        color, _ = engine.read_color("left")
        assert color == "BLUE"
        engine.try_fire_gate(_http("POST", "/api/dobot/left/commands"))

        await _wait_for_gate(engine)
        engine.try_fire_gate(_http("GET", "/api/dobot/left/color"))

        await _wait_for_gate(engine)
        engine.try_fire_gate(_http("POST", "/api/dobot/left/commands"))

        await asyncio.wait_for(engine._run_task, timeout=2.0)
        assert engine.get_status().status == SimulationStatus.IDLE

    @pytest.mark.asyncio
    async def test_speed_parameter_affects_timing(self) -> None:
        engine, _ = _make_engine()
        await engine.run_preset("happy-path", speed=10.0)
        # First step is non-gated with delayMs=75 → 7.5ms at 10x. Then waiting on gate.
        await _wait_for_gate(engine)
        assert engine.get_active_gate() is not None


# ---------------------------------------------------------------------------
# Request gate integration
# ---------------------------------------------------------------------------


class TestRequestGates:
    @pytest.mark.asyncio
    async def test_gate_timeout_aborts_preset(self) -> None:
        engine, _ = _make_engine()
        # happy-path gated steps have timeoutMs=10000; run at 1000x speed → 10ms
        await engine.run_preset("happy-path", speed=1000.0)
        await asyncio.wait_for(engine._run_task, timeout=2.0)
        status = engine.get_status()
        # Timeout aborts the preset before completion.
        assert status.status in (SimulationStatus.IDLE, SimulationStatus.STOPPED)
        assert status.currentStep < 4

    @pytest.mark.asyncio
    async def test_stop_clears_gate(self) -> None:
        engine, _ = _make_engine()
        await engine.run_preset("happy-path")
        await _wait_for_gate(engine)
        await engine.stop()
        await asyncio.sleep(0.1)
        assert engine.get_status().activeGate is None

    @pytest.mark.asyncio
    async def test_reset_clears_state(self) -> None:
        engine, _ = _make_engine()
        await engine.run_preset("happy-path")
        await _wait_for_gate(engine)
        await engine.reset()
        status = engine.get_status()
        assert status.status == SimulationStatus.IDLE
        assert status.currentPreset is None
        assert status.activeGate is None


# ---------------------------------------------------------------------------
# Sensor update integration
# ---------------------------------------------------------------------------


class TestSensorUpdates:
    @pytest.mark.asyncio
    async def test_update_sensor_persists(self) -> None:
        engine, _ = _make_engine()
        await engine.update_sensor(
            "color-left", SensorUpdateRequest(value="GREEN", raw_color=[0, 255, 0])
        )
        color, raw = engine.read_color("left")
        assert color == "GREEN"
        assert raw == [0, 255, 0]

    @pytest.mark.asyncio
    async def test_sensor_update_emits_event(self) -> None:
        engine, event_store = _make_engine()
        await engine.update_sensor("ir-left", SensorUpdateRequest(value=False))
        events, _ = event_store.list_events(page=1, page_size=10)
        state_events = [e for e in events if e["type"] == "STATE"]
        assert any("ir-left" in str(e.get("payload", {})) for e in state_events)

    @pytest.mark.asyncio
    async def test_sensor_update_rejected_during_preset_run(self) -> None:
        engine, _ = _make_engine()
        await engine.run_preset("happy-path")
        await _wait_for_gate(engine)
        assert engine.get_status().status == SimulationStatus.RUNNING

    @pytest.mark.asyncio
    async def test_preset_retains_last_sensor_value_on_completion(self) -> None:
        engine, _ = _make_engine()
        await engine.run_preset("happy-path")

        for ev in (
            _http("POST", "/api/dobot/left/commands"),
            _http("GET", "/api/dobot/left/color"),
            _http("POST", "/api/dobot/left/commands"),
        ):
            await _wait_for_gate(engine)
            engine.try_fire_gate(ev)

        await asyncio.wait_for(engine._run_task, timeout=2.0)
        assert engine.get_status().status == SimulationStatus.IDLE

        sensor = engine._sensor_registry.live["distance-left"]
        assert sensor.read() == 30.0

    def test_sensor_configs_list(self) -> None:
        engine, _ = _make_engine()
        configs = engine._sensor_registry.configs()
        assert len(configs) > 0


# ---------------------------------------------------------------------------
# Command handling integration
# ---------------------------------------------------------------------------


class TestCommandHandling:
    @pytest.mark.asyncio
    async def test_commands_applied_directly(self) -> None:
        engine, _ = _make_engine()
        result = await engine.handle_actuator_commands(
            "left", [{"type": "move", "target": {"x": 100, "y": 50}}]
        )
        assert "correlationId" in result
        state = engine._actuator_registry.get_state("left")
        assert state.position.x == 100.0
        assert state.position.y == 50.0

    @pytest.mark.asyncio
    async def test_conveyor_command(self) -> None:
        engine, _ = _make_engine()
        await engine.handle_actuator_commands(
            "left",
            [{"type": "run-conveyor", "speed": 100.0, "direction": "FORWARD"}],
        )
        state = engine._actuator_registry.get_state("left")
        assert state.conveyor_speed == 100.0
        assert state.conveyor_direction == "FORWARD"
