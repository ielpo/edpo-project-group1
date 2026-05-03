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

All plugins must inherit from `simulated_factory.sensors.base.BaseSensor` and implement two abstract methods:

```python
from simulated_factory.sensors.base import BaseSensor
from typing import Any

class MySensorSensor(BaseSensor):

    def read(self, step: int = 0) -> Any:
        """Return the current sensor value.
        
        step: 1-based simulation step index. Use for scripted sensors that
        return different values at different steps. Ignore for sensors with
        independent logic.
        """
        ...

    def update(self, value: Any) -> None:
        """Set the sensor value (called by preset sensorUpdates)."""
        ...
```

The base class provides the following ready-to-use helpers:

| Method / Property                         | Description                                               |
|-------------------------------------------|-----------------------------------------------------------|
| `self._cfg`                               | Internal `SensorConfig` Pydantic model for data storage   |
| `self.sensor_id`                          | The sensor's ID string from config                        |
| `self.value` / `self.value = x`           | Shorthand for `self._cfg.value`                           |
| `self.mode`                               | Shorthand for `self._cfg.mode`                            |
| `self.scripted_values`                    | Shorthand for `self._cfg.scripted_values`                 |
| `self.apply_update_request(data: dict)`   | Apply a `SensorUpdateRequest` dict to internal config     |
| `self.apply_overrides(overrides: dict)`   | Apply preset `sensor_overrides`                           |
| `self.clone() -> BaseSensor`              | Deep-copy this plugin (called per preset run)             |
| `self.to_sensor_config() -> SensorConfig` | Return deep copy of internal config (used by MQTT publish)|
| `self.to_dict() -> dict`                  | Serialize for API responses                               |

---

## Accessing Config Values

All fields from `config.yml` are available via `self._cfg` (as `SensorConfig` attributes) and also in the raw `config` dict passed to `__init__`. Standard fields are:

| Field            | Type         | Purpose                                          |
|------------------|--------------|--------------------------------------------------|
| `mode`           | `str`        | `"fixed"` or `"scripted"`                        |
| `value`          | `Any`        | Current value for fixed mode                     |
| `scripted_values`| `list`       | Step-indexed values for scripted mode            |
| `mqtt_topic`     | `str`        | MQTT topic override (distance sensors)           |
| `uid`            | `str`        | Sensor UID for MQTT payload                      |
| `location`       | `str`        | Sensor location for MQTT payload                 |
| `message_type`   | `str`        | Sensor message type for MQTT payload             |
| `cadence_ms`     | `int`        | Publishing cadence in milliseconds               |

Custom fields (not in the standard list) can be read from the `config` dict in `__init__`:

```python
def __init__(self, sensor_id: str, config: dict) -> None:
    super().__init__(sensor_id, config)
    self._threshold = float(config.get("threshold", 10.0))  # custom field
```

---

## Minimal Example

```python
# simulated_factory/sensors/temperature.py
from typing import Any
from simulated_factory.sensors.base import BaseSensor


class TemperatureSensor(BaseSensor):
    """Fixed or scripted temperature sensor (Celsius)."""

    def read(self, step: int = 0) -> float:
        if self._cfg.mode == "scripted" and self._cfg.scripted_values:
            index = max(step - 1, 0)
            index = min(index, len(self._cfg.scripted_values) - 1)
            return float(self._cfg.scripted_values[index])
        return float(self._cfg.value) if self._cfg.value is not None else 20.0

    def update(self, value: Any) -> None:
        self._cfg.value = value
```

Register in `config.yml`:

```yaml
defaults:
  sensors:
    temperature-room:
      type: temperature
      mode: fixed
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
      mode: fixed
      value: RED
      raw_color: [1, 0, 0]

    ir-left:
      type: ir             # loads simulated_factory.sensors.ir.IrSensor
      mode: fixed
      value: true

    distance-conveyor:
      type: distance       # loads simulated_factory.sensors.distance.DistanceSensor
      mode: scripted
      value: 30.0
      scripted_values: [30.0, 12.5, 6.2, 30.0]
      uid: TFu
      location: Conveyor
      message_type: distance_IR_short_left
      cadence_ms: 250

    # Custom sensor
    my-custom-sensor:
      type: my-custom      # loads simulated_factory.sensors.my_custom.MyCustomSensor
      mode: fixed
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

- **`sensor_overrides`** — applied via `plugin.apply_overrides(overrides)` at preset start
- **`sensorUpdates`** in steps — applied via `plugin.update(value)`
- **`publishDistance`** in steps — calls `distance_publisher.publish(plugin.to_sensor_config(), distance)`
- **`read()` calls** — `engine.read_color()` and `engine.read_ir()` delegate to `plugin.read(step)`

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
