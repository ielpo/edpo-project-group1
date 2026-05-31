# Sensor Plugin Development Guide

The simulated-factory service supports a plugin architecture for sensors.
Each sensor type is an isolated Python module in `simulated_factory/sensors/`.
New sensor types can be added without modifying the engine.

## Quick Start

1. Create a file: `simulated_factory/sensors/<type>.py`
2. Implement a class `<TitleCase>Sensor(BaseSensor)`
3. Register in `config.yml` with `type: <type>`
4. Restart the service — the engine loads plugins at startup

---

## Naming Convention

| What               | Convention                                           | Example                             |
|--------------------|------------------------------------------------------|-------------------------------------|
| Config `type`      | kebab-case                                           | `type: my-sensor`                   |
| Python file        | `simulated_factory/sensors/<type underscored>.py`   | `simulated_factory/sensors/my_sensor.py` |
| Python class       | Title-cased type + `"Sensor"`                        | `MySensorSensor`                    |

Hyphens in `type` are automatically converted to underscores for the module path and to title-casing for the class name.

---

## The `BaseSensor` Interface

All plugins must inherit from `simulated_factory.sensors.base.BaseSensor` and implement three abstract methods:

```python
from simulated_factory.sensors.base import BaseSensor
from simulated_factory.models import SensorConfig
from typing import Any

class MySensorSensor(BaseSensor):

    def __init__(self, name: str, config: SensorConfig) -> None:
        super().__init__(name, config)
        # Access config fields via self._cfg

    def read(self) -> Any:
        """Return the current sensor value."""
        ...

    def update(self, value: Any) -> None:
        """Set the sensor value (called by preset sensorUpdates)."""
        ...

    def to_dict(self) -> dict[str, Any]:
        """Serialize the sensor state for API responses."""
        ...
```

The base class provides the following ready-to-use helpers:

| Method / Property                         | Description                                               |
|-------------------------------------------|-----------------------------------------------------------|
| `self._cfg`                               | Internal `SensorConfig` Pydantic model for data storage   |
| `self.name`                               | The sensor's ID string                                    |
| `self.clone() -> BaseSensor`              | Deep-copy this plugin (called per registry reset)         |
| `self.to_config() -> SensorConfig`        | Return deep copy of internal config                       |
| `self.apply_update(data: dict)`           | Apply dict of field updates to `_cfg`                     |

---

## Accessing Config Values

All fields from `config.yml` are available via `self._cfg` (as `SensorConfig` attributes) and also in the raw `config` dict passed to `__init__`. Standard fields are:

| Field            | Type         | Purpose                                          |
|------------------|--------------|--------------------------------------------------|
| `value`          | `Any`        | Current sensor value                             |
| `mqtt_topic`     | `str`        | MQTT topic override (distance sensors)           |
| `uid`            | `str`        | Sensor UID for MQTT payload                      |
| `location`       | `str`        | Sensor location for MQTT payload                 |
| `message_type`   | `str`        | Sensor message type for MQTT payload             |
| `cadence_ms`     | `int`        | Publishing cadence in milliseconds               |

Custom fields can be added by defining a custom `SensorConfig` subclass:

```python
from pydantic import Field
from simulated_factory.models import SensorConfig

class MySensorSensorConfig(SensorConfig):
    value: float | None = None
    threshold: float = 10.0  # custom field
```

The registry will automatically pick up `<ClassName>Config` from the same module
and use it when constructing your plugin.

---

## Minimal Example

```python
# simulated_factory/sensors/temperature.py
from typing import Any

from simulated_factory.models import SensorConfig
from simulated_factory.sensors.base import BaseSensor


class TemperatureSensorConfig(SensorConfig):
    value: float | None = None
    sensorId: str = ""


class TemperatureSensor(BaseSensor):
    """Temperature sensor (Celsius)."""

    def __init__(self, name: str, config: Any) -> None:
        if isinstance(config, dict):
            cfg_dict = dict(config)
            cfg_dict.setdefault("name", name)
            cfg_dict.setdefault("type", "temperature")
            cfg_dict.setdefault("sensorId", name)
            cfg = TemperatureSensorConfig(**cfg_dict)
        elif isinstance(config, TemperatureSensorConfig):
            cfg = config
        else:
            cfg = config
        super().__init__(name, cfg)

    def read(self) -> float:
        return float(self._cfg.value) if self._cfg.value is not None else 20.0

    def update(self, value: Any) -> None:
        self._cfg.value = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensorId": self.name,
            "type": self._cfg.type,
            "value": self._cfg.value,
        }
```

Register in `config.yml`:

```yaml
defaults:
  sensors:
    temperature-room:
      type: temperature
      value: 22.5
```

---

## config.yml Registration

```yaml
defaults:
  sensors:
    # Built-in sensors
    color-left:
      type: color          # loads simulated_factory.sensors.color.ColorSensor
      value: RED
      raw_color: [1, 0, 0]

    ir-left:
      type: ir             # loads simulated_factory.sensors.ir.IrSensor
      value: true

    distance-left:
      type: distance       # loads simulated_factory.sensors.distance.DistanceSensor
      value: 30.0
      mqtt_topic: Tinkerforge/Conveyor/distance_IR_short_TFu
      uid: TFu
      location: Conveyor
      message_type: distance_IR_short
      cadence_ms: 250

    # Custom sensor
    my-custom-sensor:
      type: my-custom      # loads simulated_factory.sensors.my_custom.MyCustomSensor
      value: 42
      my_field: some_value  # custom config field
```

> **Tip**: If no `type` is specified, the engine infers it from the sensor ID prefix:
> - `color-*` → `color`
> - `ir-*` → `ir`
> - `distance-*` → `distance`
> - Anything else → `generic` (simple value store)

---

## Preset Integration

Sensor plugins work transparently with existing preset definitions:

- **`sensorUpdates`** in steps — applied via `sensor_registry.apply_updates()` which calls `plugin.update(value)`
- **`read()` calls** — `engine.read_color()` and `engine.read_ir()` delegate to `plugin.read()`
- **API updates** — `PUT /api/config/sensors/{id}` calls `plugin.apply_update(data)` which sets matching `_cfg` fields
- **Locking** — While a preset is running, the API rejects manual sensor updates with `409 Conflict`

No changes to preset YAML are needed when switching from built-in to custom sensors.

---

## Error Handling

If a sensor plugin fails to load, the service will **refuse to start** with a clear error message:

```
RuntimeError: Sensor plugin for 'my-sensor' (type='my-type') not found.
Expected module 'simulated_factory.sensors.my_type'.
Original error: No module named 'simulated_factory.sensors.my_type'
```

Common causes:
- File not found: check that `simulated_factory/sensors/my_type.py` exists
- Wrong class name: verify the class is named `MyTypeSensor` (title-cased type + "Sensor")
- Import error in your plugin: check for syntax or dependency issues in the plugin file

---

## See Also

- [`simulated_factory/sensors/example_custom.py`](simulated_factory/sensors/example_custom.py) — annotated example plugin
- [`simulated_factory/sensors/base.py`](simulated_factory/sensors/base.py) — `BaseSensor` implementation
- [`simulated_factory/sensors/color.py`](simulated_factory/sensors/color.py) — built-in color sensor (reference implementation)
