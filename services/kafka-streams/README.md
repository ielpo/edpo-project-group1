# kafka-streams

Kafka Streams service for block detection and inventory tracking (Exercise 7).

Consumes sensor events from Kafka, joins block-detected events with colour readings, and maintains a queryable inventory of all detected blocks.

## Topology

```
sensor.block-detected.v1   ←  factory service (block placed on conveyor)
        │
sensor.color.raw.v1        ←  color sensor activated by factory service per block
        →  filter UNKNOWN  →  classify RGB
        │
        └─→  stream-stream join (60 s window + 1 s grace, keyed by cubeId)
                       │
                       ├─→  inventory.blocks.v1
                       ├─→  KTable "inventory-store"  (interactive queries)
                       └─→  KTable "block-count-per-minute-store"  (windowed count per sensor)
```

**Join contract**: both `sensor.block-detected.v1` and `sensor.color.raw.v1` must use the `cubeId` as the Kafka message key. Both events must arrive within 60 seconds of each other.

## Running

Requires Kafka on `localhost:9092`.

```bash
mvn spring-boot:run
```

Or use the `KafkaStreams` IntelliJ run configuration.

## REST API (port 8104)

| Endpoint | Description |
|----------|-------------|
| `GET /inventory` | All detected blocks (cubeId → color) |
| `GET /inventory/{cubeId}` | Single block entry |
| `GET /inventory/stats/blocks-per-minute` | Windowed block count per sensor (1-minute tumbling window) |

## Topics

| Topic | Direction | Content |
|-------|-----------|---------|
| `sensor.block-detected.v1` | in | Block arrival events with cubeId (published by factory service) |
| `sensor.color.raw.v1` | in | Raw RGB readings from color sensor, keyed by cubeId |
| `inventory.blocks.v1` | out | Enriched block + color events |

## Configuration

| Property | Default | Description |
|----------|---------|-------------|
| `spring.kafka.bootstrap-servers` | `localhost:9092` | Kafka broker |
