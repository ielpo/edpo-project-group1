import logging
import os
from typing import Any, Dict

from simulated_factory.actuator_registry import ActuatorRegistry
from simulated_factory.adapters.inventory_poller import InventoryPoller
from simulated_factory.adapters.mqtt_publisher import MqttPublisher
from simulated_factory.adapters.kafka_observer import KafkaObserver
from simulated_factory.engine import SimulationEngine
from simulated_factory.events import EventBridge, EventStore
from simulated_factory.sensor_registry import SensorRegistry


def build_dependencies(
    config_path: str, logger: logging.Logger | None = None
) -> Dict[str, Any]:
    """Create and wire service dependencies for the simulated factory.

    Returns a dict with keys: event_store, mqtt_publisher,
    sensor_registry, actuator_registry, inventory_poller, engine, kafka_observer.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    event_store = EventStore()
    mqtt_publisher = MqttPublisher(
        broker_url=os.getenv("SIMULATOR_BROKER_URL"),
        event_store=event_store,
        logger=logger,
    )
    sensor_registry = SensorRegistry(config_path, mqtt_publisher=mqtt_publisher)
    actuator_registry = ActuatorRegistry()
    inventory_poller = InventoryPoller(
        url=os.getenv("INVENTORY_URL"),
        logger=logger,
    )
    engine = SimulationEngine(
        event_store=event_store,
        mqtt_publisher=mqtt_publisher,
        sensor_registry=sensor_registry,
        actuator_registry=actuator_registry,
    )

    kafka_observer = KafkaObserver(
        event_store=event_store, logger=logger, gate_firer=engine
    )

    return {
        "event_store": event_store,
        "mqtt_publisher": mqtt_publisher,
        "sensor_registry": sensor_registry,
        "actuator_registry": actuator_registry,
        "inventory_poller": inventory_poller,
        "engine": engine,
        "kafka_observer": kafka_observer,
    }
