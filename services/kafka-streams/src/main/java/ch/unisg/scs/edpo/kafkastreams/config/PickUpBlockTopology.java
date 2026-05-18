package ch.unisg.scs.edpo.kafkastreams.config;

import ch.unisg.scs.edpo.kafkastreams.domain.BlockPickUpTriggerEvent;
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

// Kafka Streams topology for triggering the robot arm when a block arrives at the right sensor.
//
// Topology (matches MoveBlockTopology diagram, right branch, in kafka-streaming-topology.drawio):
//
//  [sensor.distance.right.raw.v1]  ← right conveyor sensor publishes raw distances; no key
//    → filter                      (distance < 25.0 = block detected in front of right sensor)
//    → selectKey                   ("distance-sensor-right")
//    → groupByKey + aggregate      (rising-edge detection: emit once when gap > 2 s)
//    → filter                      (keep only rising-edge events)
//    → mapValues                   (wrap in BlockPickUpTriggerEvent)
//    → mapValues                   (wrap in RobotArmCommandEvent "PICK_AND_PLACE")
//    → [control.robot-arm.commands.v1]
@Configuration
public class PickUpBlockTopology {

    private static final float BLOCK_DISTANCE_THRESHOLD = 25.0f;
    private static final long BLOCK_ABSENCE_GAP_MS = Duration.ofSeconds(2).toMillis();

    private record BlockPresenceState(long lastSeenTimestamp, boolean risingEdge, long edgeTimestamp) {}

    @Value("${kafka.topics.distance-raw-right}")
    private String distanceRawRightTopic;

    @Value("${kafka.topics.robot-arm-commands}")
    private String robotArmCommandsTopic;

    @Bean
    public KStream<String, RobotArmCommandEvent> buildPickUpBlockTopology(StreamsBuilder builder, ObjectMapper objectMapper) {
        KStream<String, DistanceEvent> distanceRawRightStream = builder.stream(
                distanceRawRightTopic,
                Consumed.with(Serdes.String(), new JsonSerde<>(DistanceEvent.class, objectMapper))
        );

        // Filter: keep only readings where a block is present in front of the right sensor.
        KStream<String, DistanceEvent> blockPresentStream = distanceRawRightStream
                .filter((key, event) -> event.distance() < BLOCK_DISTANCE_THRESHOLD)
                .selectKey((key, value) -> "distance-sensor-right");

        // Rising-edge detection: emit once when a block appears after an inactivity gap of ≥ 2 s.
        KTable<String, BlockPresenceState> blockPresentEdges = blockPresentStream
                .groupByKey(Grouped.with(Serdes.String(), new JsonSerde<>(DistanceEvent.class, objectMapper)))
                .aggregate(
                        () -> new BlockPresenceState(Long.MIN_VALUE, false, 0L),
                        (key, event, previous) -> {
                            boolean risingEdge = (event.timestamp() - previous.lastSeenTimestamp()) > BLOCK_ABSENCE_GAP_MS;
                            long edgeTimestamp = risingEdge ? event.timestamp() : previous.edgeTimestamp();
                            return new BlockPresenceState(event.timestamp(), risingEdge, edgeTimestamp);
                        },
                        Materialized.<String, BlockPresenceState, KeyValueStore<Bytes, byte[]>>as("pick-up-block-edge-store")
                                .withKeySerde(Serdes.String())
                                .withValueSerde(new JsonSerde<>(BlockPresenceState.class, objectMapper))
                );

        KStream<String, BlockPickUpTriggerEvent> pickUpTriggerStream = blockPresentEdges
                .toStream()
                .filter((key, state) -> state != null && state.risingEdge())
                .mapValues(state -> new BlockPickUpTriggerEvent(UUID.randomUUID().toString(), state.edgeTimestamp()));

        KStream<String, RobotArmCommandEvent> robotArmCommandStream = pickUpTriggerStream
                .mapValues(trigger -> new RobotArmCommandEvent("PICK_AND_PLACE", trigger.triggerId(), trigger.timestamp()));

        robotArmCommandStream.to(
                robotArmCommandsTopic,
                Produced.with(Serdes.String(), new JsonSerde<>(RobotArmCommandEvent.class, objectMapper))
        );

        return robotArmCommandStream;
    }
}

