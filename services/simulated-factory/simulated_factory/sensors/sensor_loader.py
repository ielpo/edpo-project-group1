import importlib
from typing import Any, Type
from simulated_factory.sensors.base import BaseSensor
from simulated_factory.models import SensorConfig


def load_sensor(sensor_module: str, sensor_class: str, name: str, config_data: dict[str, Any]) -> BaseSensor:
    """Dynamically load a sensor and its configuration."""
    module = importlib.import_module(sensor_module)
    sensor_cls: Type[BaseSensor] = getattr(module, sensor_class)
    config_cls: Type[SensorConfig] = getattr(module, f"{sensor_class}Config")
    config = config_cls(name=name, **config_data)
    return sensor_cls(name=name, config=config)
