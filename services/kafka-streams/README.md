# kafka-streams

Kafka Streams service for restocking block detection, color enrichment, command triggering, and queryable inventory materialization.

The service contains three topology slices:

1. Left sensor block detection and color enrichment.
2. Left sensor conveyor-stop triggering.
3. Right sensor robot-arm pick-up triggering.

All custom payloads use the local `JsonSerde<T>` implementation backed by Jackson 3.

## Topologies

### Left sensor and inventory

1. `sensor.distance.raw.v1` is filtered to readings below `25.0` and rekeyed to `distance-sensor`.
2. Each filtered reading is published to `sensor.block-present.v1` as an internal signal for `MoveBlockTopology`.
3. A custom wall-clock processor emits one `BlockDetectedEvent` after `3 s` of inactivity, using a `200 ms` punctuation interval so detection still happens when no new records arrive.
4. `sensor.color.raw.v1` is classified to `RED`, `GREEN`, `BLUE`, or `YELLOW`; unknown colors are dropped.
5. Detected blocks and classified colors are joined in a `10 s` sliding window on the internal key `sliding-window-join`.
6. The first joined color per `cubeId` is materialized in `inventory-store` and published to `inventory.blocks.v1`.

### Conveyor stop commands

`MoveBlockTopology` consumes `sensor.block-present.v1` and emits exactly one `STOP` command to `control.conveyor.commands.v1` for each new left-sensor rising edge after at least `2 s` of inactivity.

### Robot arm pick-up commands

`PickUpBlockTopology` consumes `sensor.distance.right.raw.v1` and emits exactly one `PICK_AND_PLACE` command to `control.robot-arm.commands.v1` for each new right-sensor rising edge after at least `2 s` of inactivity.

## Running

Requires Kafka on `localhost:9092`.

```bash
mvn spring-boot:run
```

Or use the `KafkaStreams` IntelliJ run configuration. The service listens on port `8104`.

## REST API

| Endpoint | Description |
|----------|-------------|
| `GET /inventory` | All detected blocks currently materialized in `inventory-store` |
| `GET /inventory/{cubeId}` | A single inventory entry by `cubeId` |

## Topic contract

| Topic | Direction | Contract | Notes |
|-------|-----------|----------|-------|
| `sensor.distance.raw.v1` | in | external | Raw left distance sensor readings |
| `sensor.distance.right.raw.v1` | in | external | Raw right distance sensor readings |
| `sensor.color.raw.v1` | in | external | Raw RGB readings |
| `sensor.block-present.v1` | out | internal | Filtered left-sensor readings used by `MoveBlockTopology` |
| `sensor.block-detected.v1` | out | internal/diagnostic | Left-sensor inactivity detections keyed as `sliding-window-join` |
| `color.classified.v1` | out | internal/diagnostic | Classified valid colors before the sliding-window join |
| `inventory.blocks.v1` | out | supported | First-win inventory events keyed by `cubeId` |
| `control.conveyor.commands.v1` | out | supported | `STOP` commands for the conveyor |
| `control.robot-arm.commands.v1` | out | supported | `PICK_AND_PLACE` commands for the robot arm |
