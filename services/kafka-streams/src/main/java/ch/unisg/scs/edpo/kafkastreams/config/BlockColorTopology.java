package ch.unisg.scs.edpo.kafkastreams.config;

import ch.unisg.scs.edpo.kafkastreams.domain.*;
import ch.unisg.scs.edpo.kafkastreams.serde.JsonSerde;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.common.utils.Bytes;
import org.apache.kafka.streams.KeyValue;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.kstream.*;
import org.apache.kafka.streams.state.KeyValueStore;
import org.apache.kafka.streams.state.SessionStore;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import tools.jackson.databind.ObjectMapper;

import java.time.Duration;
import java.util.UUID;

// Kafka Streams topology for block detection and color classification.
//
// Topology (matches kafka-streaming-topology.drawio):
//
//  [sensor.distance.raw.v1]     ← conveyor sensor publishes continuously; no key
//    → filter          (distance < 25.0 = block present)
//    → selectKey       ("distance-sensor")
//    → groupByKey + Session Window (2 s inactivity gap)
//    → count + Suppress (emit once when session closes)   ← "Compress into one event"
//    → map             (generate cubeId UUID)
//    → KStream<cubeId, BlockDetectedEvent>
//          │
//          ├─ to [sensor.block-detected.v1]               ← new-block-events
//          │
//          └─ selectKey ("color-sensor")
//                 │
//  [sensor.color.raw.v1]        ← color sensor streams raw RGB; no key
//    → mapValues       (classify RGB → BlockColor)
//    → filter          (discard non-RGBY)
//    → selectKey       ("color-sensor")
//                 │
//                 └─ stream-stream Sliding Window Join (10 s)
//                        │
//                        └─ selectKey (cubeId) + groupByKey + reduce(first)
//                               │
//                               └─ KTable "inventory-store" → toStream → [inventory.blocks.v1]
@Configuration
public class BlockColorTopology {

    @Value("${kafka.topics.distance-raw}")
    private String distanceTopic;

    @Value("${kafka.topics.color-raw}")
    private String colorRawTopic;

    @Value("${kafka.topics.block-detected}")
    private String blockDetectedTopic;

    @Value("${kafka.topics.block-present}")
    private String blockPresentTopic;

    @Value("${kafka.topics.inventory-blocks}")
    private String inventoryBlocksTopic;

    @Bean
    public KStream<String, BlockColorEvent> buildBlockColorTopology(StreamsBuilder builder, ObjectMapper objectMapper) {

        // ──-- Distance branch ────────────────────────────────────────────────────────────
        // Translation (Map) + Filter: keep only readings where a block is present.

        KStream<String, DistanceEvent> distanceStream = builder.stream(
                distanceTopic,
                Consumed.with(Serdes.String(), new JsonSerde<>(DistanceEvent.class, objectMapper))
        );

        KStream<String, DistanceEvent> blockPresentStream = distanceStream
                .filter((key, event) -> event.distance() < 25.0f)
                .selectKey((key, value) -> "distance-sensor");

        // Publish each block-present reading so other topologies can consume them directly.
        blockPresentStream.to(
                blockPresentTopic,
                Produced.with(Serdes.String(), new JsonSerde<>(DistanceEvent.class, objectMapper))
        );

        // Session Window: group bursts of block-present readings into one session per block.
        // Suppress: emit only the final count when the session closes (inactivity gap expires).
        // "Compress into one event": the count collapses N readings into a single Long.

        KTable<Windowed<String>, Long> blockSessions = blockPresentStream
                .groupByKey(Grouped.with(Serdes.String(), new JsonSerde<>(DistanceEvent.class, objectMapper)))
                .windowedBy(SessionWindows.ofInactivityGapWithNoGrace(Duration.ofSeconds(2)))
                .count(Materialized.<String, Long, SessionStore<Bytes, byte[]>>as("block-session-store")
                        .withKeySerde(Serdes.String())
                        .withValueSerde(Serdes.Long()))
                .suppress(Suppressed.untilWindowCloses(Suppressed.BufferConfig.unbounded().shutDownWhenFull()));

        // Rekey: generate a UUID as cubeId for each detected block.

        KStream<String, BlockDetectedEvent> blockDetectedStream = blockSessions
                .toStream()
                .map((windowedKey, count) -> {
                    String cubeId = UUID.randomUUID().toString();
                    long timestamp = windowedKey.window().end();
                    return KeyValue.pair(cubeId, new BlockDetectedEvent(cubeId, timestamp));
                });

        // Write confirmed block detection to output topic (new-block-events).
        blockDetectedStream.to(blockDetectedTopic,
                Produced.with(Serdes.String(), new JsonSerde<>(BlockDetectedEvent.class, objectMapper)));

        // ── Color branch ───────────────────────────────────────────────────────────────
        // Translation (Map) + Filter: classify RGB and discard non-RGBY readings.
        // Filter before rekeying to reduce repartitioning cost.

        KStream<String, ColorEvent> colorRawStream = builder.stream(
                colorRawTopic,
                Consumed.with(Serdes.String(), new JsonSerde<>(ColorEvent.class, objectMapper))
        );

        KStream<String, BlockColor> classifiedColorStream = colorRawStream
                .mapValues(event -> BlockColor.from(event.r(), event.g(), event.b()))
                .filter((key, color) -> color != BlockColor.UNKNOWN)
                .selectKey((key, value) -> "color-sensor");

        // ── Sliding Window Join ────────────────────────────────────────────────────────
        // Both streams rekeyed to "color-sensor". Events within 10 s of each other are joined.
        // cubeId comes from the BlockDetectedEvent.

        KStream<String, BlockColorEvent> joinedStream = blockDetectedStream
                .selectKey((key, value) -> "color-sensor")
                .join(
                        classifiedColorStream,
                        (block, color) -> new BlockColorEvent(block.cubeId(), color, block.timestamp()),
                        JoinWindows.ofTimeDifferenceAndGrace(Duration.ofSeconds(10), Duration.ofSeconds(1)),
                        StreamJoined.with(
                                Serdes.String(),
                                new JsonSerde<>(BlockDetectedEvent.class, objectMapper),
                                new JsonSerde<>(BlockColor.class, objectMapper)
                        )
                );

        // ── First-color-per-cube ───────────────────────────────────────────────────────
        // Rekey to cubeId, reduce to keep only the first valid color seen per cube.
        // With default caching, toStream() emits exactly once per cubeId.

        KTable<String, BlockColorEvent> inventoryTable = joinedStream
                .selectKey((key, value) -> value.cubeId())
                .groupByKey(Grouped.with(Serdes.String(), new JsonSerde<>(BlockColorEvent.class, objectMapper)))
                .reduce(
                        (first, next) -> first,
                        Materialized.<String, BlockColorEvent, KeyValueStore<Bytes, byte[]>>as("inventory-store")
                                .withKeySerde(Serdes.String())
                                .withValueSerde(new JsonSerde<>(BlockColorEvent.class, objectMapper))
                );

        KStream<String, BlockColorEvent> blockColorStream = inventoryTable.toStream();
        blockColorStream.to(inventoryBlocksTopic,
                Produced.with(Serdes.String(), new JsonSerde<>(BlockColorEvent.class, objectMapper)));

        return blockColorStream;
    }
}


