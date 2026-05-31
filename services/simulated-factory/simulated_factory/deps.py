import logging
import os
from typing import Any, Dict

from simulated_factory.adapters.inventory_poller import InventoryPoller
from simulated_factory.adapters.mqtt_publisher import MqttPublisher
from simulated_factory.adapters.kafka_observer import KafkaObserver
from simulated_factory.engine import SimulationEngine
from simulated_factory.events import EventBridge, EventStore


def build_dependencies(
    config_path: str, logger: logging.Logger | None = None
) -> Dict[str, Any]:
    """Create and wire service dependencies for the simulated factory.

    Returns a dict with keys: event_store, event_bridge, mqtt_publisher,
    engine, kafka_observer.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    event_store = EventStore()
    event_bridge = EventBridge(
        mode=os.getenv("SIMULATOR_EVENT_BRIDGE", "none"),
        target_url=os.getenv("SIMULATOR_EVENT_BRIDGE_URL"),
        logger=logger,
    )
    mqtt_publisher = MqttPublisher(
        broker_url=os.getenv("SIMULATOR_BROKER_URL"),
        event_store=event_store,
        logger=logger,
    )
    inventory_poller = InventoryPoller(
        url=os.getenv("INVENTORY_URL"),
        logger=logger,
    )
    engine = SimulationEngine(
        config_path=config_path,
        event_store=event_store,
        mqtt_publisher=mqtt_publisher,
        event_bridge=event_bridge,
        inventory_poller=inventory_poller,
    )

    kafka_observer = KafkaObserver(event_store=event_store, logger=logger)

    return {
        "event_store": event_store,
        "event_bridge": event_bridge,
        "mqtt_publisher": mqtt_publisher,
        "inventory_poller": inventory_poller,
        "engine": engine,
        "kafka_observer": kafka_observer,
    }
