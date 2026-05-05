package ch.unisg.scs.edpo.kafkastreams.config;

import ch.unisg.scs.edpo.kafkastreams.domain.*;
import ch.unisg.scs.edpo.kafkastreams.serde.JsonSerde;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.common.utils.Bytes;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.kstream.*;
import org.apache.kafka.streams.state.KeyValueStore;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import tools.jackson.databind.ObjectMapper;

import java.time.Duration;

// Kafka Streams topology for block tracking and inventory enrichment.
//
// Topology (matches kafka-streaming-topology.drawio):
//
//  [sensor.block-detected.v1]   ← published externally (e.g. manual button trigger)
//    → KStream<cubeId, BlockDetectedEvent>
//          │
//  [sensor.color.v1]
//    → mapValues       (stateless: classify raw RGB → BlockColor)
//    → filter          (stateless: discard UNKNOWN readings)
//    → KStream<cubeId, BlockColor>
//          │
//          └─ stream-stream join (60 s window)
//                │
//                ▼
//         KStream<cubeId, BlockColorEvent>
//                │
//                ├─ to [inventory.blocks.v1]
//                ├─ toTable → KTable "inventory-store"  (interactive queries)
//                └─ groupBy + windowedBy → KTable "block-count-per-minute-store" (windowed)
@Configuration
public class TopologyConfig {

    @Value("${kafka.topics.color}")
    private String colorTopic;

    @Value("${kafka.topics.block-detected}")
    private String blockDetectedTopic;

    @Value("${kafka.topics.inventory-blocks}")
    private String inventoryBlocksTopic;

    @Bean
    public KStream<String, BlockColorEvent> blockColorStream(StreamsBuilder builder, ObjectMapper objectMapper) {

        // ── Block-detected branch ──────────────────────────────────────────────────────
        // Published externally (manual trigger / button); cubeId is the message key.

        KStream<String, BlockDetectedEvent> blockStream = builder.stream(
                blockDetectedTopic,
                Consumed.with(Serdes.String(), new JsonSerde<>(BlockDetectedEvent.class, objectMapper))
        );

        // ── Color branch ───────────────────────────────────────────────────────────────

        KStream<String, ColorEvent> colorStream = builder.stream(
                colorTopic,
                Consumed.with(Serdes.String(), new JsonSerde<>(ColorEvent.class, objectMapper))
        );

        // Stateless — classification: map raw RGB to a known BlockColor
        KStream<String, BlockColor> classifiedColorStream = colorStream
                .mapValues(event -> BlockColor.from(event.r(), event.g(), event.b()))
                // Stateless — filter: discard readings that couldn't be classified
                .filter((key, color) -> color != BlockColor.UNKNOWN);

        // ── Join ───────────────────────────────────────────────────────────────────────
        // Stream-stream join keyed by cubeId.
        // Both sides must arrive within 60 s of each other.
        // Producer contract for sensor.color.v1: message key must be the cubeId.

        KStream<String, BlockColorEvent> joinedStream = blockStream.join(
                classifiedColorStream,
                (block, color) -> new BlockColorEvent(block.cubeId(), color, block.timestamp()),
                JoinWindows.ofTimeDifferenceWithNoGrace(Duration.ofSeconds(60)),
                StreamJoined.with(
                        Serdes.String(),
                        new JsonSerde<>(BlockDetectedEvent.class, objectMapper),
                        new JsonSerde<>(BlockColor.class, objectMapper)
                )
        );

        // Write enriched events to output topic
        joinedStream.to(inventoryBlocksTopic, Produced.with(Serdes.String(), new JsonSerde<>(BlockColorEvent.class, objectMapper)));

        // ── Inventory KTable (stateful, interactive queries) ───────────────────────────
        // Materialised store keyed by cubeId — queryable via GET /inventory
        joinedStream.toTable(
                Materialized.<String, BlockColorEvent, KeyValueStore<Bytes, byte[]>>as("inventory-store")
                        .withKeySerde(Serdes.String())
                        .withValueSerde(new JsonSerde<>(BlockColorEvent.class, objectMapper))
        );

        // ── Windowed aggregation (stateful, windowed) ──────────────────────────────────
        // Count block arrivals per sensor per tumbling 1-minute window.
        // Queryable via GET /inventory/stats/blocks-per-minute
        blockStream
                .groupBy(
                        (key, block) -> block.sensorUid(),
                        Grouped.with(Serdes.String(), new JsonSerde<>(BlockDetectedEvent.class, objectMapper))
                )
                .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(1)))
                .count(Materialized.as("block-count-per-minute-store"));

        return joinedStream;
    }
}
