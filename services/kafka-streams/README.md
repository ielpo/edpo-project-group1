# kafka-streams

Kafka Streams service for block detection and inventory tracking (Exercise 7).

Consumes distance and colour sensor events, detects blocks via a session window, joins with colour readings, and maintains a queryable inventory.

## Topology

```
sensor.distance.raw.v1     ← conveyor distance sensor (continuous readings)
        │
        filter (distance < 25.0 = block present)
        │
        Session Window (2 s inactivity gap)
        │
        Suppress (emit once when session closes)   "compress into one event"
        │
        map → generate cubeId (UUID)
        │
        ├─→  sensor.block-detected.v1              new-block-events
        │
        └─→  selectKey("color-sensor")
                       │
sensor.color.raw.v1        ← colour sensor (continuous readings, no key)
        filter (discard non-RGBY)
        selectKey("color-sensor")
                       │
                       └─→  Sliding Window Join (10 s)
                                      │
                                      reduce(first colour per cube)
                                      │
                                      ├─→  inventory.blocks.v1
                                      └─→  KTable "inventory-store"
```

## Running

Requires Kafka on `localhost:9092`.

```bash
mvn spring-boot:run
```

Or use the `KafkaStreams` IntelliJ run configuration. Runs on port 8104.

## REST API

| Endpoint | Description |
|----------|-------------|
| `GET /inventory` | All detected blocks (cubeId → color) |
| `GET /inventory/{cubeId}` | Single block entry |

## Topics

| Topic | Direction | Content |
|-------|-----------|---------|
| `sensor.distance.raw.v1` | in | Raw distance readings from conveyor sensor |
| `sensor.color.raw.v1` | in | Raw RGB readings from colour sensor (no key) |
| `sensor.block-detected.v1` | out | Confirmed block detection with generated cubeId |
| `inventory.blocks.v1` | out | Enriched block + colour event (first colour per cube) |
