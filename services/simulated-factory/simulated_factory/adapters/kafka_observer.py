"""Passive Kafka consumer that records process-topic messages as KAFKA events.

The observer subscribes to a fixed set of process topics and appends each
consumed record to the local EventStore. It never produces or acts on commands;
its sole responsibility is making process-topic activity visible in the
simulator UI alongside other event sources.

Connection failures are non-fatal: the rest of the simulator continues to work
even if Kafka is unreachable.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Iterable

try:  # pragma: no cover - import guard exercised at runtime only
    from aiokafka import AIOKafkaConsumer
    from aiokafka.errors import KafkaError
except Exception:  # pragma: no cover - aiokafka is a hard dep, but stay defensive
    AIOKafkaConsumer = None  # type: ignore[assignment]
    KafkaError = Exception  # type: ignore[assignment,misc]

from simulated_factory.events import EventStore


DEFAULT_BOOTSTRAP_SERVERS = "localhost:9092"
DEFAULT_GROUP_ID = "simulated-factory"
DEFAULT_TOPICS: tuple[str, ...] = (
    "order.manufacture.v1",
    "order.complete.v1",
    "info.v1",
    "error.v1",
)

# Environment opt-out used to keep tests and constrained deployments from
# attempting a real Kafka connection. Production defaults to enabled.
ENV_OBSERVER_FLAG = "SIMULATED_FACTORY_KAFKA_OBSERVER"


def _observer_enabled_by_env() -> bool:
    raw = os.getenv(ENV_OBSERVER_FLAG)
    if raw is None:
        return True
    return raw.strip().lower() not in ("0", "false", "no", "off", "disabled")


def _decode_value(value: bytes | None) -> Any:
    if value is None:
        return None
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError:
        return {"raw": repr(value)}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


class KafkaObserver:
    """Async observer that streams process topics into the EventStore."""

    def __init__(
        self,
        *,
        event_store: EventStore,
        logger: logging.Logger,
        bootstrap_servers: str = DEFAULT_BOOTSTRAP_SERVERS,
        group_id: str = DEFAULT_GROUP_ID,
        topics: Iterable[str] = DEFAULT_TOPICS,
        consumer_factory: Any = None,
    ) -> None:
        self.event_store = event_store
        self.logger = logger
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topics: tuple[str, ...] = tuple(topics)
        self._consumer_factory = consumer_factory or AIOKafkaConsumer
        self._consumer: Any = None
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start consuming. Connection runs in the background so application
        startup is never blocked by a slow or unreachable broker. Failures are
        logged and leave the observer stopped without affecting the service."""
        if self._running:
            return
        if not _observer_enabled_by_env():
            self.logger.info(
                "Kafka observer disabled by %s environment variable",
                ENV_OBSERVER_FLAG,
            )
            return
        if self._consumer_factory is None:
            self.logger.warning(
                "Kafka observer cannot start: aiokafka is not available"
            )
            return

        self._running = True
        self._task = asyncio.create_task(
            self._run(), name="kafka-observer"
        )

    async def _run(self) -> None:
        try:
            self._consumer = self._consumer_factory(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                enable_auto_commit=True,
                auto_offset_reset="latest",
            )
            await self._consumer.start()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.logger.warning(
                "Kafka observer failed to connect to %s: %s",
                self.bootstrap_servers,
                exc,
            )
            consumer = self._consumer
            self._consumer = None
            self._running = False
            if consumer is not None:
                try:
                    await consumer.stop()
                except Exception:  # pragma: no cover - best effort cleanup
                    pass
            return

        self.logger.info(
            "Kafka observer started (topics=%s group=%s bootstrap=%s)",
            ",".join(self.topics),
            self.group_id,
            self.bootstrap_servers,
        )
        await self._consume_loop()

    async def stop(self) -> None:
        self._running = False
        task = self._task
        self._task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        if self._consumer is not None:
            try:
                await self._consumer.stop()
            except Exception:  # pragma: no cover - best effort
                pass
            self._consumer = None

    async def _consume_loop(self) -> None:
        consumer = self._consumer
        if consumer is None:
            return
        try:
            async for record in consumer:
                await self._record_event(record)
        except asyncio.CancelledError:
            raise
        except KafkaError as exc:
            self.logger.warning("Kafka observer loop terminated: %s", exc)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.exception("Unexpected error in Kafka observer loop: %s", exc)

    async def _record_event(self, record: Any) -> None:
        topic = getattr(record, "topic", None)
        decoded = _decode_value(getattr(record, "value", None))
        key_bytes = getattr(record, "key", None)
        key = None
        if isinstance(key_bytes, (bytes, bytearray)):
            try:
                key = key_bytes.decode("utf-8")
            except UnicodeDecodeError:
                key = repr(bytes(key_bytes))
        elif key_bytes is not None:
            key = str(key_bytes)

        await self.event_store.append(
            "KAFKA",
            source="kafka",
            message=f"Consumed message from {topic}",
            topic=topic,
            payload={
                "topic": topic,
                "partition": getattr(record, "partition", None),
                "offset": getattr(record, "offset", None),
                "key": key,
                "value": decoded,
            },
        )
