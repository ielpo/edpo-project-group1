from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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
    sensorId: str
    mode: str = "fixed"
    value: Any = None
    raw_color: list[int] = Field(default_factory=lambda: [0, 0, 0])
    scripted_values: list[Any] = Field(default_factory=list)
    failRate: float = 0.0
    mqtt_topic: str | None = None
    uid: str = "TFu"
    location: str = "Conveyor"
    message_type: str = "distance_IR_short_left"
    cadence_ms: int = 1000


class PresetStep(BaseModel):
    name: str
    delayMs: int = 100
    note: str | None = None
    publishDistance: float | None = None
    sensorUpdates: dict[str, Any] = Field(default_factory=dict)


class PresetDefinition(BaseModel):
    name: str
    description: str = ""
    sensor_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    steps: list[PresetStep] = Field(default_factory=list)


class SimulationState(BaseModel):
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
    speed: str = "normal"


class SensorUpdateRequest(BaseModel):
    mode: str | None = None
    value: Any = None
    raw_color: list[int] | None = None
    scripted_values: list[Any] | None = None
    failRate: float | None = None
