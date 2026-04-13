package com.experiments;

import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.AdminClientConfig;
import org.apache.kafka.clients.admin.ListConsumerGroupOffsetsResult;
import org.apache.kafka.clients.admin.ListOffsetsResult;
import org.apache.kafka.clients.admin.OffsetSpec;
import org.apache.kafka.common.TopicPartition;

import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;
import java.util.concurrent.ExecutionException;

/**
 * LagMonitor — polls Kafka's AdminClient every 2 seconds and prints the
 * consumer lag for each partition of "gaze-events" in the "lag-experiment-group".
 *
 * Run this alongside SlowConsumer to get quantitative lag measurements for
 * each experiment scenario.
 *
 * Sample output:
 *   [12:00:01] partition=0 | logStart=    0 | committed=  142 | logEnd=  260 | lag=  118
 *   [12:00:01] partition=1 | logStart=    0 | committed=  139 | logEnd=  258 | lag=  119
 *   [12:00:03] partition=0 | logStart=  200 | committed=  142 | logEnd=  520 | lag=  378 | *** DATA LOSS: 58 records deleted before consumer reached them ***
 *   ...
 *
 * Scenario D — Retention-Based Record Loss:
 *   Before running, set a short retention on the topic:
 *     docker exec -it <kafka-container> kafka-configs --bootstrap-server localhost:9092 \
 *       --alter --entity-type topics --entity-name gaze-events \
 *       --add-config retention.ms=15000
 *   Then run SlowConsumer with PROCESSING_DELAY_MS=200.
 *   When logStart advances past committed, records are permanently lost.
 */
public class LagMonitor {

    private static final String BOOTSTRAP_SERVERS = "localhost:9092";
    private static final String GROUP_ID          = "lag-experiment-group";
    private static final String TOPIC             = "gaze-events";
    private static final int    POLL_INTERVAL_MS  = 2000;
    private static final int    NUM_PARTITIONS    = 2;

    private static final DateTimeFormatter TIME_FMT =
            DateTimeFormatter.ofPattern("HH:mm:ss");

    public static void main(String[] args) throws InterruptedException {

        Properties adminProps = new Properties();
        adminProps.put(AdminClientConfig.BOOTSTRAP_SERVERS_CONFIG, BOOTSTRAP_SERVERS);

        try (AdminClient admin = AdminClient.create(adminProps)) {

            System.out.println("[LagMonitor] Started. Polling every "
                    + POLL_INTERVAL_MS + " ms for group=" + GROUP_ID
                    + " topic=" + TOPIC);
            System.out.printf("%-12s %-12s %-12s %-12s %-12s %-8s%n",
                    "Time", "Partition", "LogStart", "Committed", "LogEnd", "Lag");
            System.out.println("-".repeat(80));

            while (true) {
                try {
                    // 1. Fetch committed offsets for the consumer group
                    ListConsumerGroupOffsetsResult offsetsResult =
                            admin.listConsumerGroupOffsets(GROUP_ID);
                    Map<TopicPartition, org.apache.kafka.clients.consumer.OffsetAndMetadata> committed =
                            offsetsResult.partitionsToOffsetAndMetadata().get();

                    // 2. Build requests for log-start and log-end offsets
                    Map<TopicPartition, OffsetSpec> logEndRequest = new HashMap<>();
                    Map<TopicPartition, OffsetSpec> logStartRequest = new HashMap<>();
                    for (int p = 0; p < NUM_PARTITIONS; p++) {
                        TopicPartition tp = new TopicPartition(TOPIC, p);
                        logEndRequest.put(tp, OffsetSpec.latest());
                        logStartRequest.put(tp, OffsetSpec.earliest());
                    }
                    Map<TopicPartition, ListOffsetsResult.ListOffsetsResultInfo> logEndOffsets =
                            admin.listOffsets(logEndRequest).all().get();
                    Map<TopicPartition, ListOffsetsResult.ListOffsetsResultInfo> logStartOffsets =
                            admin.listOffsets(logStartRequest).all().get();

                    // 3. Print lag per partition
                    String now = LocalTime.now().format(TIME_FMT);
                    for (int p = 0; p < NUM_PARTITIONS; p++) {
                        TopicPartition tp = new TopicPartition(TOPIC, p);

                        long logEnd = logEndOffsets.containsKey(tp)
                                ? logEndOffsets.get(tp).offset() : -1L;
                        long logStart = logStartOffsets.containsKey(tp)
                                ? logStartOffsets.get(tp).offset() : -1L;

                        org.apache.kafka.clients.consumer.OffsetAndMetadata committedMeta =
                                committed.get(tp);
                        long committedOffset = (committedMeta != null)
                                ? committedMeta.offset()
                                : -1L;

                        long lag = (committedOffset >= 0 && logEnd >= 0)
                                ? logEnd - committedOffset : -1L;

                        long lost = (logStart > committedOffset && committedOffset >= 0)
                                ? logStart - committedOffset : 0L;

                        String lossWarning = lost > 0
                                ? " | *** DATA LOSS: " + lost + " records deleted before consumer reached them ***"
                                : "";

                        System.out.printf("[%-8s] partition=%-2d | logStart=%6d | committed=%6d | logEnd=%6d | lag=%6s%s%n",
                                now, p, logStart, committedOffset, logEnd,
                                lag >= 0 ? String.valueOf(lag) : "N/A",
                                lossWarning);
                    }
                    System.out.println();

                } catch (ExecutionException e) {
                    System.err.println("[LagMonitor] AdminClient error: " + e.getCause().getMessage());
                }

                Thread.sleep(POLL_INTERVAL_MS);
            }
        }
    }
}
