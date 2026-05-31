from abc import ABC, abstractmethod
from typing import Any


class BaseActuator(ABC):
    """Abstract base class all actuator plugins must implement.

    Mirrors :class:`BaseSensor`. An actuator receives a name at construction
    and exposes two operations: applying a batch of commands and reporting a
    deep copy of its current state.

    Subclasses MUST implement :meth:`apply` and :meth:`state`.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def apply(self, commands: list[dict]) -> None:
        """Apply a batch of commands, mutating internal state."""

    @abstractmethod
    def state(self) -> Any:
        """Return a deep copy of the actuator's current state."""
