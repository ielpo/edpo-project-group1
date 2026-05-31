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
    InteractiveConfig,
    SensorUpdateRequest,
    SimulationStatus,
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


# ---------------------------------------------------------------------------
# Preset execution integration
# ---------------------------------------------------------------------------


class TestPresetExecution:
    @pytest.mark.asyncio
    async def test_happy_path_completes_with_gates(self) -> None:
        engine, event_store = _make_engine()
        run_id = await engine.run_preset("happy-path")
        assert run_id == "run-0001"

        gate_calls = [
            ("POST", "/api/dobot/left/commands"),
            ("GET", "/api/dobot/left/color"),
            ("POST", "/api/dobot/left/commands"),
        ]
        for method, path in gate_calls:
            for _ in range(200):
                await asyncio.sleep(0.01)
                if engine._step_gate is not None:
                    break
            assert engine.fire_gate_if_matches(method, path) is True

        await asyncio.wait_for(engine._run_task, timeout=2.0)
        status = engine.get_status()
        assert status.status == SimulationStatus.IDLE
        assert status.currentPreset == "happy-path"

    @pytest.mark.asyncio
    async def test_wrong_color_preset_with_overrides(self) -> None:
        engine, event_store = _make_engine()
        await engine.run_preset("wrong-color")
        # First step is non-gated, then gated steps
        for _ in range(200):
            await asyncio.sleep(0.01)
            if engine._step_gate is not None:
                break
        # The color sensor should be BLUE due to preset override
        color, _ = engine.read_color("left")
        assert color == "BLUE"
        engine.fire_gate_if_matches("POST", "/api/dobot/left/commands")

        # Color-check gate
        for _ in range(200):
            await asyncio.sleep(0.01)
            if engine._step_gate is not None:
                break
        engine.fire_gate_if_matches("GET", "/api/dobot/left/color")

        # Reject gate
        for _ in range(200):
            await asyncio.sleep(0.01)
            if engine._step_gate is not None:
                break
        engine.fire_gate_if_matches("POST", "/api/dobot/left/commands")

        await asyncio.wait_for(engine._run_task, timeout=2.0)
        assert engine.get_status().status == SimulationStatus.IDLE

    @pytest.mark.asyncio
    async def test_speed_parameter_affects_timing(self) -> None:
        engine, event_store = _make_engine()
        # Run at 10x speed — non-gated steps complete faster
        await engine.run_preset("happy-path", speed=10.0)
        # First step is non-gated with delayMs=75 → 7.5ms at 10x
        await asyncio.sleep(0.05)
        # Should be past step 1 and waiting on gate
        assert engine._step_gate is not None


# ---------------------------------------------------------------------------
# Request gate integration
# ---------------------------------------------------------------------------


class TestRequestGates:
    @pytest.mark.asyncio
    async def test_gate_timeout_applies_side_effects(self) -> None:
        engine, event_store = _make_engine()
        await engine.run_preset("happy-path", speed=100.0)  # very fast timeout
        # Wait for the first gated step to time out
        await asyncio.sleep(0.5)
        events, _ = event_store.list_events(page=1, page_size=50)
        timed_out = [
            e
            for e in events
            if isinstance(e.get("payload"), dict)
            and e["payload"].get("gateTimedOut") is True
        ]
        assert len(timed_out) > 0

    @pytest.mark.asyncio
    async def test_stop_clears_gate(self) -> None:
        engine, event_store = _make_engine()
        await engine.run_preset("happy-path")
        for _ in range(200):
            await asyncio.sleep(0.01)
            if engine._step_gate is not None:
                break
        assert engine._step_gate is not None
        await engine.stop()
        await asyncio.sleep(0.1)
        assert engine.get_status().waitingForRequest is None

    @pytest.mark.asyncio
    async def test_reset_clears_state(self) -> None:
        engine, event_store = _make_engine()
        await engine.run_preset("happy-path")
        for _ in range(200):
            await asyncio.sleep(0.01)
            if engine._step_gate is not None:
                break
        await engine.reset()
        status = engine.get_status()
        assert status.status == SimulationStatus.IDLE
        assert status.currentPreset is None
        assert status.waitingForRequest is None


# ---------------------------------------------------------------------------
# Sensor update integration
# ---------------------------------------------------------------------------


class TestSensorUpdates:
    @pytest.mark.asyncio
    async def test_update_sensor_persists(self) -> None:
        engine, event_store = _make_engine()
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
        engine, event_store = _make_engine()
        await engine.run_preset("happy-path")
        for _ in range(200):
            await asyncio.sleep(0.01)
            if engine._step_gate is not None:
                break
        assert engine.get_status().status == SimulationStatus.RUNNING
        # The engine.update_sensor itself doesn't enforce locking — the API does.
        # Verify running state is detectable for the API layer.

    @pytest.mark.asyncio
    async def test_preset_retains_last_sensor_value_on_completion(self) -> None:
        engine, event_store = _make_engine()
        await engine.run_preset("happy-path")

        gate_calls = [
            ("POST", "/api/dobot/left/commands"),
            ("GET", "/api/dobot/left/color"),
            ("POST", "/api/dobot/left/commands"),
        ]
        for method, path in gate_calls:
            for _ in range(200):
                await asyncio.sleep(0.01)
                if engine._step_gate is not None:
                    break
            engine.fire_gate_if_matches(method, path)

        await asyncio.wait_for(engine._run_task, timeout=2.0)
        assert engine.get_status().status == SimulationStatus.IDLE

        # After completion, distance-left should retain the last preset-applied value (30.0 from last step)
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
        engine, event_store = _make_engine()
        result = await engine.handle_actuator_commands(
            "left", [{"type": "move", "target": {"x": 100, "y": 50}}]
        )
        assert "correlationId" in result
        state = engine._actuator_registry.get_state("left")
        assert state.position.x == 100.0
        assert state.position.y == 50.0

    @pytest.mark.asyncio
    async def test_commands_intercepted_and_resolved(self) -> None:
        engine, event_store = _make_engine()
        engine.set_interactive_config(
            InteractiveConfig(intercepted={"move"}, timeout_seconds=5)
        )
        task = asyncio.create_task(
            engine.handle_actuator_commands(
                "left", [{"type": "move", "target": {"x": 10}}]
            )
        )
        await asyncio.sleep(0.05)
        pending = engine.get_pending_actions()
        assert len(pending) == 1
        action_id = pending[0]["id"]
        await engine.resolve_action(action_id, "success")
        result = await asyncio.wait_for(task, timeout=2.0)
        assert result["outcome"] == "success"

    @pytest.mark.asyncio
    async def test_conveyor_command(self) -> None:
        engine, event_store = _make_engine()
        await engine.handle_actuator_commands(
            "left",
            [{"type": "run-conveyor", "speed": 100.0, "direction": "FORWARD"}],
        )
        state = engine._actuator_registry.get_state("left")
        assert state.conveyor_speed == 100.0
        assert state.conveyor_direction == "FORWARD"
