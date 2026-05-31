import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SimulationStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"


class Position(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    r: float = 0.0


class DobotRuntimeState(BaseModel):
    position: Position = Field(default_factory=Position)
    speed: float = 50.0
    acceleration: float = 100.0
    suction_enabled: bool = False
    conveyor_speed: float = 0.0
    conveyor_distance: float = 0.0
    conveyor_direction: str = "STOP"
    last_command: str | None = None


class SensorConfig(BaseModel):
    name: str = ""
    type: str = ""
    sensorId: str = ""


class AwaitRequest(BaseModel):
    method: str
    path: str


class PresetStep(BaseModel):
    name: str
    delayMs: int = 100
    note: str | None = None
    triggerMqtt: bool = False
    sensorUpdates: dict[str, Any] = Field(default_factory=dict)
    awaitRequest: AwaitRequest | None = None


class PresetDefinition(BaseModel):
    name: str
    description: str = ""
    steps: list[PresetStep] = Field(default_factory=list)


class EngineLifecycleState(BaseModel):
    """Lifecycle-only engine status — no dobot or sensor state."""

    id: str = "run-0000"
    status: SimulationStatus = SimulationStatus.IDLE
    currentPreset: str | None = None
    currentStep: int = 0
    currentStepName: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    waitingForRequest: AwaitRequest | None = None


class SimulationState(BaseModel):
    """Public /api/status payload — composed outside the engine."""

    id: str = "run-0000"
    status: SimulationStatus = SimulationStatus.IDLE
    currentPreset: str | None = None
    currentStep: int = 0
    currentStepName: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    dobots: dict[str, DobotRuntimeState] = Field(
        default_factory=lambda: {
            "left": DobotRuntimeState(),
            "right": DobotRuntimeState(),
        }
    )
    waitingForRequest: AwaitRequest | None = None


class EventEntry(BaseModel):
    id: str
    ts: datetime = Field(default_factory=utc_now)
    type: str
    source: str | None = None
    message: str | None = None
    topic: str | None = None
    endpoint: str | None = None
    method: str | None = None
    statusCode: int | None = None
    payload: Any = None


class RunPresetRequest(BaseModel):
    preset: str
    speed: float = 1.0


class SensorUpdateRequest(BaseModel):
    value: Any = None
    raw_color: list[int] | None = None

    @field_validator("raw_color", mode="before")
    @classmethod
    def coerce_raw_color(cls, v: Any) -> list[int] | None:
        if v is None:
            return None
        if isinstance(v, str):
            tokens = [t.strip() for t in v.split(",") if t.strip()]
            if not tokens:
                return None
            result: list[int] = []
            for t in tokens:
                try:
                    result.append(int(t))
                except (ValueError, TypeError):
                    try:
                        result.append(int(float(t)))
                    except (ValueError, TypeError):
                        result.append(0)
            return result
        if isinstance(v, list):
            result = []
            for item in v:
                if item is None or (isinstance(item, str) and item.strip() == ""):
                    continue
                if isinstance(item, (int, float)):
                    result.append(int(item))
                else:
                    try:
                        result.append(int(str(item).strip()))
                    except (ValueError, TypeError):
                        try:
                            result.append(int(float(str(item).strip())))
                        except (ValueError, TypeError):
                            result.append(0)
            return result if result else None
        return v

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value(cls, v: Any) -> Any:
        if not isinstance(v, str):
            return v
        s = v.strip()
        if s == "":
            return None
        lowered = s.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        try:
            if "." in s:
                return float(s)
            return int(s)
        except ValueError:
            return s


class InteractiveConfig(BaseModel):
    intercepted: set[str] = Field(default_factory=set)
    timeout_seconds: int = 30


class InteractiveConfigRequest(BaseModel):
    intercepted: list[str] = Field(default_factory=list)
    timeoutSeconds: int = 30


class ResolveActionRequest(BaseModel):
    outcome: str
    reason: str | None = None


@dataclass
class PendingAction:
    id: str
    robot_name: str
    commands: list[Any]
    correlation_id: str
    created_at: datetime = field(default_factory=utc_now)
    outcome: str | None = None
    reason: str | None = None
    timed_out: bool = False
    _event: asyncio.Event = field(default_factory=asyncio.Event)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "robotName": self.robot_name,
            "commands": self.commands,
            "commandTypes": [
                str(cmd.get("type", "unknown")) if isinstance(cmd, dict) else "unknown"
                for cmd in self.commands
            ],
            "correlationId": self.correlation_id,
            "createdAt": self.created_at.isoformat(),
        }

    async def wait_for_resolution(self, timeout: float | None = None) -> bool:
        """Wait for the action to be resolved.

        Returns True if the action was resolved before the timeout, False if
        the wait timed out.
        """
        try:
            if timeout is None:
                await self._event.wait()
                return True
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    def resolve(self, outcome: str, reason: str | None = None) -> None:
        """Mark the action as resolved and notify any waiter."""
        self.outcome = outcome
        self.reason = reason
        self._event.set()

    def mark_timed_out(self) -> None:
        """Convenience to mark the action as timed out and notify waiters."""
        self.timed_out = True
        self._event.set()
