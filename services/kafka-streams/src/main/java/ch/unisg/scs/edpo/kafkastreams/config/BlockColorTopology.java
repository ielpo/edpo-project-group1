package ch.unisg.scs.edpo.kafkastreams.config;

import ch.unisg.scs.edpo.kafkastreams.domain.*;
import ch.unisg.scs.edpo.kafkastreams.serde.JsonSerde;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.common.utils.Bytes;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.kstream.*;
import org.apache.kafka.streams.processor.api.Processor;
import org.apache.kafka.streams.processor.api.ProcessorContext;
import org.apache.kafka.streams.processor.api.Record;
import org.apache.kafka.streams.processor.PunctuationType;
import org.apache.kafka.streams.state.KeyValueIterator;
import org.apache.kafka.streams.state.KeyValueStore;
import org.apache.kafka.streams.state.Stores;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import tools.jackson.databind.ObjectMapper;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

// Kafka Streams topology for left-sensor block detection, color enrichment, and inventory materialization.
//
// Left sensor / inventory flow:
//  [sensor.distance.raw.v1]
//    → filter(distance < 25.0)
//    → selectKey("distance-sensor")
//    → publish [sensor.block-present.v1]                 internal signal for MoveBlockTopology
//    → wall-clock inactivity processor                   3 s gap, 200 ms punctuation
//    → publish [sensor.block-detected.v1]                internal/diagnostic join-side stream
//
// Color enrichment flow:
//  [sensor.color.raw.v1]
//    → classify RGB → BlockColor
//    → filter(valid RED/GREEN/BLUE/YELLOW only)
//    → selectKey("sliding-window-join")
//    → publish [color.classified.v1]                     internal/diagnostic stream
//
// Join and materialization:
//  detected blocks + classified colors
//    → sliding window join (10 s)
//    → selectKey(cubeId)
//    → reduce(first joined color wins)
//    → KTable "inventory-store"
//    → publish [inventory.blocks.v1]
@Configuration
public class BlockColorTopology {

    private static final String BLOCK_ACTIVITY_STORE = "block-activity-store";
    private static final Duration BLOCK_ABSENCE_GAP = Duration.ofSeconds(3);
    private static final Duration PUNCTUATION_INTERVAL = Duration.ofMillis(200);

    @Value("${kafka.topics.distance-raw}")
    private String distanceTopic;

    @Value("${kafka.topics.color-raw}")
    private String colorRawTopic;

    @Value("${kafka.topics.block-detected}")
    private String blockDetectedTopic;

    @Value("${kafka.topics.block-present}")
    private String blockPresentTopic;

        @Value("${kafka.topics.color-classified}")
        private String colorClassifiedTopic;

    @Value("${kafka.topics.inventory-blocks}")
    private String inventoryBlocksTopic;

    @Bean
    public KStream<String, BlockColorEvent> buildBlockColorTopology(StreamsBuilder builder, ObjectMapper objectMapper) {

        /// Distance branch
        // Filter: keep only readings where a block is present.
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

        builder.addStateStore(
                Stores.keyValueStoreBuilder(
                        Stores.persistentKeyValueStore(BLOCK_ACTIVITY_STORE),
                        Serdes.String(),
                        Serdes.Long()
                )
        );

        // Wall-clock inactivity detection: emits when a key has been quiet for BLOCK_ABSENCE_GAP,
        // even if no new records arrive to advance stream time.
        KStream<String, BlockDetectedEvent> blockDetectedStream = blockPresentStream
                .process(BlockInactivityProcessor::new, BLOCK_ACTIVITY_STORE);

        // Force a repartition on the final join key so join tasks see both streams on matching partitions.
        KStream<String, BlockDetectedEvent> blockDetectedForJoin = blockDetectedStream
                .selectKey((key, value) -> "sliding-window-join")
                .repartition(Repartitioned.with(
                        Serdes.String(),
                        new JsonSerde<>(BlockDetectedEvent.class, objectMapper)
                ));

        // Keep the detected-block stream visible for diagnostics; the topic key is the internal join key.
        blockDetectedStream
                .selectKey((key, value) -> "sliding-window-join")
                .to(blockDetectedTopic,
                        Produced.with(Serdes.String(), new JsonSerde<>(BlockDetectedEvent.class, objectMapper)));

        /// Color branch
        // Translation (Map) + Filter: classify raw RGB and discard invalid readings.
        // Filter before rekeying to reduce repartitioning cost.
        KStream<String, ColorEvent> colorRawStream = builder.stream(
                colorRawTopic,
                Consumed.with(Serdes.String(), new JsonSerde<>(ColorEvent.class, objectMapper))
        );

        KStream<String, BlockColor> classifiedColorStream = colorRawStream
                .mapValues(event -> BlockColor.from(event.r(), event.g(), event.b()))
                .filter((key, color) -> color != BlockColor.UNKNOWN)
                .selectKey((key, value) -> "sliding-window-join");

        KStream<String, BlockColor> classifiedColorForJoin = classifiedColorStream
                .repartition(Repartitioned.with(
                        Serdes.String(),
                        new JsonSerde<>(BlockColor.class, objectMapper)
                ));

        // Keep the classified-color stream visible for diagnostics alongside the join input.
        classifiedColorStream.to(
                colorClassifiedTopic,
                Produced.with(Serdes.String(), new JsonSerde<>(BlockColor.class, objectMapper))
        );

        /// Sliding Window Join
        // Both streams have key "sliding-window-join". Events within 10 s of each other are joined.
        // cubeId comes from the BlockDetectedEvent.
        KStream<String, BlockColorEvent> joinedStream = blockDetectedForJoin
                .join(
                        classifiedColorForJoin,
                        (block, color) -> new BlockColorEvent(block.cubeId(), color, block.timestamp()),
                        JoinWindows.ofTimeDifferenceAndGrace(Duration.ofSeconds(10), Duration.ofSeconds(1)),
                        StreamJoined.with(
                                Serdes.String(),
                                new JsonSerde<>(BlockDetectedEvent.class, objectMapper),
                                new JsonSerde<>(BlockColor.class, objectMapper)
                        )
                );

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

    private static final class BlockInactivityProcessor implements Processor<String, DistanceEvent, String, BlockDetectedEvent> {
        private ProcessorContext<String, BlockDetectedEvent> context;
        private KeyValueStore<String, Long> activityStore;

        @Override
        public void init(ProcessorContext<String, BlockDetectedEvent> processorContext) {
            this.context = processorContext;
            this.activityStore = processorContext.getStateStore(BLOCK_ACTIVITY_STORE);

            // Wall-clock punctuation allows inactivity detection even when stream-time is not advancing.
            this.context.schedule(PUNCTUATION_INTERVAL, PunctuationType.WALL_CLOCK_TIME, wallClockTime -> {
                List<String> expiredKeys = new ArrayList<>();
                try (KeyValueIterator<String, Long> entries = activityStore.all()) {
                    while (entries.hasNext()) {
                        var entry = entries.next();
                        if (wallClockTime - entry.value >= BLOCK_ABSENCE_GAP.toMillis()) {
                            expiredKeys.add(entry.key);
                        }
                    }
                }

                for (String expiredKey : expiredKeys) {
                    String cubeId = UUID.randomUUID().toString();
                    context.forward(new Record<>(
                            "sliding-window-join",
                            new BlockDetectedEvent(cubeId, wallClockTime),
                            wallClockTime
                    ));
                    activityStore.delete(expiredKey);
                }
            });
        }

        @Override
        public void process(Record<String, DistanceEvent> record) {
                        activityStore.put(record.key(), context.currentSystemTimeMs());
        }

        @Override
        public void close() {
        }
    }
}


