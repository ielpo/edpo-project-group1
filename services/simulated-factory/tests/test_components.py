"""Unit tests for the extracted simulation components (process runner, control points, resource layer)."""

import asyncio
import logging
from pathlib import Path

import pytest

from simulated_factory.adapters.distance_publisher import DistancePublisher
from simulated_factory.engine.control_points import ControlPointManager
from simulated_factory.engine.process_runner import ProcessRunner
from simulated_factory.engine.resources import ResourceManager
from simulated_factory.engine.runtime import (
    ControlState,
    FactoryState,
    PhysicalResources,
    ProcessState,
    SimulationRuntime,
)
from simulated_factory.events import EventStore
from simulated_factory.models import (
    AwaitRequest,
    DobotRuntimeState,
    InteractiveConfig,
    PresetDefinition,
    PresetStep,
    SensorUpdateRequest,
    SimulationStatus,
)

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yml"
LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_runtime() -> SimulationRuntime:
    return SimulationRuntime()


def _make_resource_mgr(runtime: SimulationRuntime) -> ResourceManager:
    event_store = EventStore()
    mgr = ResourceManager(
        resources=runtime.resources,
        event_store=event_store,
        config_path=str(CONFIG_PATH),
    )
    mgr.set_current_step_getter(lambda: runtime.process.current_step)
    return mgr


def _make_process_runner(
    runtime: SimulationRuntime, event_store: EventStore
) -> ProcessRunner:
    dp = DistancePublisher(None, event_store, LOGGER)
    return ProcessRunner(
        factory=runtime.factory,
        process=runtime.process,
        control=runtime.control,
        resources=runtime.resources,
        event_store=event_store,
        distance_publisher=dp,
    )


def _make_control_mgr(
    runtime: SimulationRuntime, event_store: EventStore
) -> ControlPointManager:
    return ControlPointManager(
        factory=runtime.factory,
        process=runtime.process,
        control=runtime.control,
        resources=runtime.resources,
        event_store=event_store,
    )


# ---------------------------------------------------------------------------
# ProcessRunner unit tests
# ---------------------------------------------------------------------------


class TestProcessRunner:
    @pytest.mark.asyncio
    async def test_list_presets_returns_names(self) -> None:
        rt = _make_runtime()
        rt.process.presets = {
            "test": PresetDefinition(
                name="test",
                description="A test preset",
                steps=[PresetStep(name="step-1")],
            )
        }
        event_store = EventStore()
        runner = _make_process_runner(rt, event_store)
        presets = runner.list_presets()
        assert len(presets) == 1
        assert presets[0]["name"] == "test"
        assert presets[0]["steps"] == [{"name": "step-1"}]

    @pytest.mark.asyncio
    async def test_run_preset_unknown_raises_key_error(self) -> None:
        rt = _make_runtime()
        event_store = EventStore()
        runner = _make_process_runner(rt, event_store)
        with pytest.raises(KeyError):
            await runner.run_preset("nonexistent")

    @pytest.mark.asyncio
    async def test_run_preset_advances_state(self) -> None:
        rt = _make_runtime()
        rt.process.presets = {
            "simple": PresetDefinition(
                name="simple",
                steps=[
                    PresetStep(name="s1", delayMs=10),
                    PresetStep(name="s2", delayMs=10),
                ],
            )
        }
        event_store = EventStore()
        runner = _make_process_runner(rt, event_store)
        run_id = await runner.run_preset("simple")
        assert run_id == "run-0001"
        assert rt.factory.status == SimulationStatus.RUNNING
        await asyncio.wait_for(rt.factory.run_task, timeout=1.0)
        assert rt.factory.status == SimulationStatus.IDLE
        assert rt.process.current_step == 2

    @pytest.mark.asyncio
    async def test_stop_requested_halts_preset(self) -> None:
        rt = _make_runtime()
        rt.process.presets = {
            "long": PresetDefinition(
                name="long",
                steps=[
                    PresetStep(name="s1", delayMs=500),
                    PresetStep(name="s2", delayMs=500),
                ],
            )
        }
        event_store = EventStore()
        runner = _make_process_runner(rt, event_store)
        await runner.run_preset("long")
        await asyncio.sleep(0.05)
        rt.factory.stop_requested = True
        await asyncio.wait_for(rt.factory.run_task, timeout=2.0)
        assert rt.factory.status == SimulationStatus.STOPPED

    @pytest.mark.asyncio
    async def test_clear_step_gate_sets_event(self) -> None:
        rt = _make_runtime()
        event_store = EventStore()
        runner = _make_process_runner(rt, event_store)
        evt = asyncio.Event()
        step = PresetStep(name="gated", awaitRequest=AwaitRequest(method="GET", path="/x"))
        rt.control.step_gate = (step.awaitRequest, evt, step)
        runner._clear_step_gate()
        assert evt.is_set()
        assert rt.control.step_gate is None


# ---------------------------------------------------------------------------
# ControlPointManager unit tests
# ---------------------------------------------------------------------------


class TestControlPointManager:
    def test_fire_gate_if_matches_returns_nothing_when_no_gate(self) -> None:
        rt = _make_runtime()
        event_store = EventStore()
        mgr = _make_control_mgr(rt, event_store)
        # Should not raise
        mgr.fire_gate_if_matches("GET", "/api/test")

    def test_matches_gate_detects_active_gate(self) -> None:
        rt = _make_runtime()
        event_store = EventStore()
        mgr = _make_control_mgr(rt, event_store)
        step = PresetStep(
            name="gated",
            awaitRequest=AwaitRequest(method="POST", path="/api/dobot/{name}/commands"),
        )
        rt.control.step_gate = (step.awaitRequest, asyncio.Event(), step)
        assert mgr.matches_gate("POST", "/api/dobot/left/commands") is True
        assert mgr.matches_gate("GET", "/api/dobot/left/commands") is False
        assert mgr.matches_gate("POST", "/unrelated") is False

    @pytest.mark.asyncio
    async def test_handle_dobot_commands_no_intercept(self) -> None:
        rt = _make_runtime()
        rt.resources.dobots = {"left": DobotRuntimeState()}
        event_store = EventStore()
        mgr = _make_control_mgr(rt, event_store)
        result = await mgr.handle_dobot_commands(
            "left", [{"type": "move", "target": {"x": 10}}]
        )
        assert "correlationId" in result
        assert rt.resources.dobots["left"].position.x == 10.0

    @pytest.mark.asyncio
    async def test_resolve_action_success(self) -> None:
        rt = _make_runtime()
        rt.resources.dobots = {"left": DobotRuntimeState()}
        rt.control.interactive_config = InteractiveConfig(
            intercepted={"move"}, timeout_seconds=5
        )
        event_store = EventStore()
        mgr = _make_control_mgr(rt, event_store)

        # Start the command in background — it will wait for resolution
        task = asyncio.create_task(
            mgr.handle_dobot_commands("left", [{"type": "move", "target": {"x": 5}}])
        )
        await asyncio.sleep(0.05)

        # Resolve it
        action_id = list(rt.control.pending.keys())[0]
        action = await mgr.resolve_action(action_id, "success")
        assert action.outcome == "success"

        result = await asyncio.wait_for(task, timeout=2.0)
        assert result["outcome"] == "success"
        assert rt.resources.dobots["left"].position.x == 5.0

    def test_get_pending_actions_empty(self) -> None:
        rt = _make_runtime()
        event_store = EventStore()
        mgr = _make_control_mgr(rt, event_store)
        assert mgr.get_pending_actions() == []

    def test_set_interactive_config(self) -> None:
        rt = _make_runtime()
        event_store = EventStore()
        mgr = _make_control_mgr(rt, event_store)
        new_cfg = InteractiveConfig(intercepted={"move"}, timeout_seconds=10)
        result = mgr.set_interactive_config(new_cfg)
        assert "move" in result.intercepted
        assert result.timeout_seconds == 10


# ---------------------------------------------------------------------------
# ResourceManager unit tests
# ---------------------------------------------------------------------------


class TestResourceManager:
    def test_loads_sensors_from_config(self) -> None:
        rt = _make_runtime()
        mgr = _make_resource_mgr(rt)
        assert "color-left" in rt.resources.sensors
        assert "ir-left" in rt.resources.sensors
        assert "distance-left" in rt.resources.sensors

    def test_get_presets(self) -> None:
        rt = _make_runtime()
        mgr = _make_resource_mgr(rt)
        presets = mgr.get_presets()
        assert "happy-path" in presets
        assert presets["happy-path"].name == "happy-path"

    def test_sensor_map_for_preset_applies_overrides(self) -> None:
        rt = _make_runtime()
        mgr = _make_resource_mgr(rt)
        presets = mgr.get_presets()
        wrong_color = presets["wrong-color"]
        sensors = mgr.sensor_map_for_preset(wrong_color)
        color, _ = sensors["color-left"].read()
        assert color == "BLUE"

    def test_get_sensor_configs(self) -> None:
        rt = _make_runtime()
        mgr = _make_resource_mgr(rt)
        configs = mgr.get_sensor_configs()
        assert len(configs) > 0
        names = [c.name for c in configs]
        assert "color-left" in names

    @pytest.mark.asyncio
    async def test_update_sensor(self) -> None:
        rt = _make_runtime()
        mgr = _make_resource_mgr(rt)
        result = await mgr.update_sensor(
            "color-left", SensorUpdateRequest(value="GREEN")
        )
        assert result.value == "GREEN"

    def test_read_color(self) -> None:
        rt = _make_runtime()
        mgr = _make_resource_mgr(rt)
        color, raw = mgr.read_color("left")
        assert color == "RED"
        assert raw == [1, 0, 0]

    def test_read_ir(self) -> None:
        rt = _make_runtime()
        mgr = _make_resource_mgr(rt)
        result = mgr.read_ir("left")
        assert result is True

    def test_get_dobot_state(self) -> None:
        rt = _make_runtime()
        rt.resources.dobots = {"left": DobotRuntimeState(speed=75.0)}
        mgr = _make_resource_mgr(rt)
        state = mgr.get_dobot_state("left")
        assert state.speed == 75.0

    def test_get_inventory_cache_cold(self) -> None:
        rt = _make_runtime()
        mgr = _make_resource_mgr(rt)
        cache = mgr.get_inventory_cache()
        assert cache == {"grid": None, "rows": 0, "cols": 0}

    def test_infer_sensor_type_explicit(self) -> None:
        rt = _make_runtime()
        mgr = _make_resource_mgr(rt)
        assert mgr._infer_sensor_type("foo", {"type": "color"}) == "color"

    def test_infer_sensor_type_prefix(self) -> None:
        rt = _make_runtime()
        mgr = _make_resource_mgr(rt)
        assert mgr._infer_sensor_type("color-x", {}) == "color"
        assert mgr._infer_sensor_type("ir-y", {}) == "ir"
        assert mgr._infer_sensor_type("distance-z", {}) == "distance"
        assert mgr._infer_sensor_type("unknown", {}) == "generic"
