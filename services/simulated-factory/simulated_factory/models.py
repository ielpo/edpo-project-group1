from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


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


TriggerType = Literal["http", "kafka", "manual"]


class AwaitTrigger(BaseModel):
    """Declarative gate spec attached to a preset step.

    A single discriminated-union field replacing the old separate awaitRequest /
    interactive-interception mechanisms. ``timeoutMs`` is required so behaviour
    is explicit at the preset level.
    """

    type: TriggerType
    timeoutMs: int = 30000
    # http
    method: str | None = None
    path: str | None = None
    # kafka
    topic: str | None = None

    @model_validator(mode="after")
    def _check_type_fields(self) -> "AwaitTrigger":
        if self.type == "http":
            if not self.method or not self.path:
                raise ValueError("awaitTrigger type=http requires method and path")
        elif self.type == "kafka":
            if not self.topic:
                raise ValueError("awaitTrigger type=kafka requires topic")
        return self


@dataclass
class TriggerEvent:
    """Runtime event passed to ``SimulationEngine.try_fire_gate``."""

    type: TriggerType
    method: str | None = None
    path: str | None = None
    topic: str | None = None


class PresetStep(BaseModel):
    name: str
    delayMs: int | None = None
    note: str | None = None
    sensorUpdates: dict[str, Any] = Field(default_factory=dict)
    awaitTrigger: AwaitTrigger | None = None

    @model_validator(mode="after")
    def _check_timing(self) -> "PresetStep":
        if self.delayMs is not None and self.awaitTrigger is not None:
            raise ValueError(
                f"step {self.name!r}: delayMs and awaitTrigger are mutually exclusive"
            )
        if self.delayMs is None and self.awaitTrigger is None:
            # Default to a tiny delay so non-gated steps still advance.
            self.delayMs = 100
        return self


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
    activeGate: AwaitTrigger | None = None


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
    activeGate: AwaitTrigger | None = None


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
    r: int | None = None
    g: int | None = None
    b: int | None = None

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

    @model_validator(mode="after")
    def assemble_rgb(self) -> "SensorUpdateRequest":
        """Build raw_color from individual r/g/b slider fields when present."""
        if self.raw_color is None and any(
            v is not None for v in (self.r, self.g, self.b)
        ):
            self.raw_color = [self.r or 0, self.g or 0, self.b or 0]
        return self


@dataclass
class PendingAction:
    """UI-facing snapshot of the currently-active gate.

    The engine maintains at most one pending action at a time — the one
    corresponding to the gate currently being waited on. Manual gates render
    approve/reject buttons; other types render a read-only status card.
    """

    id: str
    step_name: str
    trigger_type: TriggerType
    trigger_spec: dict[str, Any]
    timeout_ms: int
    started_at: datetime = field(default_factory=utc_now)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "stepName": self.step_name,
            "triggerType": self.trigger_type,
            "triggerSpec": dict(self.trigger_spec),
            "timeoutMs": self.timeout_ms,
            "startedAt": self.started_at.isoformat(),
        }
