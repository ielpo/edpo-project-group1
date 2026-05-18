package ch.unisg.scs.edpo.kafkastreams.config;

import ch.unisg.scs.edpo.kafkastreams.domain.BlockMoveTriggerEvent;
import ch.unisg.scs.edpo.kafkastreams.domain.ConveyorCommandEvent;
import ch.unisg.scs.edpo.kafkastreams.domain.DistanceEvent;
import ch.unisg.scs.edpo.kafkastreams.domain.RobotArmCommandEvent;
import ch.unisg.scs.edpo.kafkastreams.serde.JsonSerde;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.common.utils.Bytes;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.kstream.Consumed;
import org.apache.kafka.streams.kstream.Grouped;
import org.apache.kafka.streams.kstream.KStream;
import org.apache.kafka.streams.kstream.KTable;
import org.apache.kafka.streams.kstream.Materialized;
import org.apache.kafka.streams.kstream.Produced;
import org.apache.kafka.streams.state.KeyValueStore;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import tools.jackson.databind.ObjectMapper;

import java.time.Duration;
import java.util.UUID;

@Configuration
public class MoveBlockTopology {

    private static final long BLOCK_ABSENCE_GAP_MS = Duration.ofSeconds(2).toMillis();

    private record BlockPresenceState(long lastSeenTimestamp, boolean risingEdge, long edgeTimestamp) {}

    @Value("${kafka.topics.block-present}")
    private String blockPresentTopic;

    @Value("${kafka.topics.conveyor-commands}")
    private String conveyorCommandsTopic;

    @Value("${kafka.topics.robot-arm-commands}")
    private String robotArmCommandsTopic;

    @Bean
    public KStream<String, RobotArmCommandEvent> moveBlockTopology(StreamsBuilder builder, ObjectMapper objectMapper) {
        KStream<String, DistanceEvent> blockPresentStream = builder.stream(
                blockPresentTopic,
                Consumed.with(Serdes.String(), new JsonSerde<>(DistanceEvent.class, objectMapper))
        );

        // Rising-edge detection: emit once when a block appears after an inactivity gap.
        KTable<String, BlockPresenceState> blockPresentEdges = blockPresentStream
                .groupByKey(Grouped.with(Serdes.String(), new JsonSerde<>(DistanceEvent.class, objectMapper)))
                .aggregate(
                        () -> new BlockPresenceState(Long.MIN_VALUE, false, 0L),
                        (key, event, previous) -> {
                            boolean risingEdge = (event.timestamp() - previous.lastSeenTimestamp()) > BLOCK_ABSENCE_GAP_MS;
                            long edgeTimestamp = risingEdge ? event.timestamp() : previous.edgeTimestamp();
                            return new BlockPresenceState(event.timestamp(), risingEdge, edgeTimestamp);
                        },
                        Materialized.<String, BlockPresenceState, KeyValueStore<Bytes, byte[]>>as("move-block-edge-store")
                            .withKeySerde(Serdes.String())
                            .withValueSerde(new JsonSerde<>(BlockPresenceState.class, objectMapper))
                );

        KStream<String, BlockMoveTriggerEvent> moveTriggerStream = blockPresentEdges
                .toStream()
                .filter((key, state) -> state.risingEdge())
                .mapValues(state -> new BlockMoveTriggerEvent(UUID.randomUUID().toString(), state.edgeTimestamp()));

        KStream<String, ConveyorCommandEvent> conveyorCommandStream = moveTriggerStream
                .mapValues(trigger -> new ConveyorCommandEvent("STOP", trigger.triggerId(), trigger.timestamp()));

        conveyorCommandStream.to(
                conveyorCommandsTopic,
                Produced.with(Serdes.String(), new JsonSerde<>(ConveyorCommandEvent.class, objectMapper))
        );

        KStream<String, RobotArmCommandEvent> robotArmCommandStream = moveTriggerStream
                .mapValues(trigger -> new RobotArmCommandEvent("PICK_AND_PLACE", trigger.triggerId(), trigger.timestamp()));

        robotArmCommandStream.to(
                robotArmCommandsTopic,
                Produced.with(Serdes.String(), new JsonSerde<>(RobotArmCommandEvent.class, objectMapper))
        );

        return robotArmCommandStream;
    }
}


