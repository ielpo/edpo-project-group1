"""Control-point manager: owns request gates, pending actions, and command interception."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from simulated_factory.models import (
    AwaitRequest,
    DobotRuntimeState,
    InteractiveConfig,
    PendingAction,
    Position,
    PresetStep,
    utc_now,
)
from simulated_factory.engine.runtime import (
    ControlState,
    FactoryState,
    PhysicalResources,
    ProcessState,
)
from simulated_factory.utils import path_pattern_to_regex

if TYPE_CHECKING:
    from simulated_factory.events import EventStore

logger = logging.getLogger(__name__)


class ControlPointManager:
    """Owns request-gated behavior, pending actions, and command resolution."""

    def __init__(
        self,
        *,
        factory: FactoryState,
        process: ProcessState,
        control: ControlState,
        resources: PhysicalResources,
        event_store: EventStore,
    ):
        self._factory = factory
        self._process = process
        self._control = control
        self._resources = resources
        self._event_store = event_store

    # ------------------------------------------------------------------
    # Gate matching and firing
    # ------------------------------------------------------------------

    def fire_gate_if_matches(self, method: str, path: str) -> None:
        """Fire the active step gate if the incoming request matches.

        This applies step side-effects synchronously so the handler that
        follows observes the updated state.
        """
        gate = self._control.step_gate
        if gate is None:
            return
        pattern, event, step = gate
        if method.upper() != pattern.method.upper():
            return
        regex = path_pattern_to_regex(pattern.path)
        if regex.match(path) is None:
            return
        # Apply step side-effects before signaling, so the triggering
        # request's handler sees updated sensor state.
        self._apply_gate_side_effects(step)
        event.set()

    def _apply_gate_side_effects(self, step: PresetStep) -> None:
        """Apply sensor updates from a gate-fired step (synchronous)."""
        for sensor_id, value in step.sensorUpdates.items():
            plugin = self._resources.sensors.get(sensor_id)
            if plugin is None:
                continue
            if hasattr(plugin, "update"):
                plugin.update(value)
            else:
                cfg = getattr(plugin, "_cfg", None)
                if cfg is not None and hasattr(cfg, "model_copy"):
                    try:
                        plugin._cfg = cfg.model_copy(update={"value": value})
                    except Exception:
                        try:
                            setattr(plugin._cfg, "value", value)
                        except Exception:
                            setattr(plugin, "value", value)
                else:
                    setattr(plugin, "value", value)

    def matches_gate(self, method: str, path: str) -> bool:
        gate = self._control.step_gate
        if gate is None:
            return False
        pattern, _event, _step = gate
        if method.upper() != pattern.method.upper():
            return False
        regex = path_pattern_to_regex(pattern.path)
        return regex.match(path) is not None

    # ------------------------------------------------------------------
    # Command interception and pending actions
    # ------------------------------------------------------------------

    async def handle_dobot_commands(
        self, robot_name: str, payload: Any
    ) -> dict[str, Any]:
        command_list = payload if isinstance(payload, list) else [payload]
        correlation_id = f"cmd-{self._factory.run_id}-{self._process.current_step + 1}"

        intercepted = self._control.interactive_config.intercepted
        command_types = [
            str(cmd.get("type", "unknown")) if isinstance(cmd, dict) else "unknown"
            for cmd in command_list
        ]
        should_intercept = bool(intercepted) and any(
            ct in intercepted for ct in command_types
        )

        if should_intercept:
            self._control.pending_counter += 1
            action_id = f"act-{self._control.pending_counter:04d}"
            action = PendingAction(
                id=action_id,
                robot_name=robot_name,
                commands=list(command_list),
                correlation_id=correlation_id,
            )
            self._control.pending[action_id] = action

            await self._record_event(
                "PENDING_ACTION",
                message=f"Pending action {action_id} for {robot_name}",
                payload={
                    "actionId": action_id,
                    "robot": robot_name,
                    "commands": command_list,
                    "commandTypes": command_types,
                    "correlationId": correlation_id,
                },
            )

            timeout = max(1, int(self._control.interactive_config.timeout_seconds))
            try:
                await asyncio.wait_for(action._event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                action.outcome = "failure"
                action.timed_out = True
                self._control.pending.pop(action_id, None)
                await self._record_event(
                    "ACTION_RESOLVED",
                    message=f"Action {action_id} timed out",
                    payload={
                        "actionId": action_id,
                        "outcome": "failure",
                        "timedOut": True,
                    },
                )

            outcome = action.outcome or "failure"
            if outcome == "success":
                self._apply_commands(robot_name, command_list)
                await self._record_event(
                    "COMMAND",
                    message=(
                        f"Accepted {len(command_list)} command(s) for {robot_name} "
                        "after interactive resolution"
                    ),
                    payload={"robot": robot_name, "commands": command_list},
                )

            result: dict[str, Any] = {
                "correlationId": correlation_id,
                "outcome": outcome,
            }
            if action.timed_out:
                result["timedOut"] = True
            return result

        self._apply_commands(robot_name, command_list)
        await self._record_event(
            "COMMAND",
            message=f"Accepted {len(command_list)} command(s) for {robot_name}",
            payload={"robot": robot_name, "commands": command_list},
        )
        return {"correlationId": correlation_id}

    def _apply_commands(self, robot_name: str, command_list: list[Any]) -> None:
        dobot_state = self._resources.dobots.setdefault(
            robot_name, DobotRuntimeState()
        )
        for command in command_list:
            command_type = str(command.get("type", "unknown"))
            match command_type:
                case "move":
                    target = command.get("target", {})
                    dobot_state.position = Position(
                        x=float(target.get("x", dobot_state.position.x)),
                        y=float(target.get("y", dobot_state.position.y)),
                        z=float(target.get("z", dobot_state.position.z)),
                        r=float(target.get("r", dobot_state.position.r)),
                    )
                case "move-relative":
                    offset = command.get("offset", {})
                    dobot_state.position.x += float(offset.get("x", 0.0) or 0.0)
                    dobot_state.position.y += float(offset.get("y", 0.0) or 0.0)
                    dobot_state.position.z += float(offset.get("z", 0.0) or 0.0)
                    dobot_state.position.r += float(offset.get("r", 0.0) or 0.0)
                case "set-speed":
                    dobot_state.speed = float(
                        command.get("speed", dobot_state.speed)
                    )
                    if command.get("acceleration") is not None:
                        dobot_state.acceleration = float(command["acceleration"])
                case "suction-cup":
                    dobot_state.suction_enabled = bool(
                        command.get("enabled", False)
                    )
                case "run-conveyor":
                    dobot_state.conveyor_speed = float(command.get("speed", 0.0))
                    dobot_state.conveyor_direction = str(
                        command.get("direction", "STOP")
                    )
                case "move-conveyor":
                    dobot_state.conveyor_speed = float(command.get("speed", 0.0))
                    dobot_state.conveyor_distance = float(
                        command.get("distance", 0.0)
                    )
                    dobot_state.conveyor_direction = str(
                        command.get("direction", "STOP")
                    )
                case _:
                    logger.info(
                        "Ignoring unsupported simulator command type %s",
                        command_type,
                    )
            dobot_state.last_command = command_type

    # ------------------------------------------------------------------
    # Action resolution
    # ------------------------------------------------------------------

    async def resolve_action(
        self, action_id: str, outcome: str, reason: str | None = None
    ) -> PendingAction:
        if outcome not in ("success", "failure"):
            raise ValueError(f"invalid outcome {outcome!r}")
        action = self._control.pending.get(action_id)
        if action is None:
            raise KeyError(action_id)
        action.outcome = outcome
        action.reason = reason
        action._event.set()
        self._control.pending.pop(action_id, None)
        await self._record_event(
            "ACTION_RESOLVED",
            message=f"Action {action_id} resolved: {outcome}",
            payload={
                "actionId": action_id,
                "outcome": outcome,
                "reason": reason,
                "timedOut": False,
            },
        )
        return action

    def get_pending_actions(self) -> list[dict[str, Any]]:
        return [action.to_public_dict() for action in self._control.pending.values()]

    def get_interactive_config(self) -> InteractiveConfig:
        return self._control.interactive_config.model_copy(deep=True)

    def set_interactive_config(self, config: InteractiveConfig) -> InteractiveConfig:
        self._control.interactive_config = config
        return self.get_interactive_config()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _record_event(self, event_type: str, **kwargs: Any) -> None:
        await self._event_store.append(event_type, **kwargs)
