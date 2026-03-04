package com.experiments;

import com.google.common.io.Resources;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;

import java.io.IOException;
import java.io.InputStream;
import java.time.Duration;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Properties;

/**
 * SlowConsumer — demonstrates consumer lag and rebalance triggering.
 *
 * Scenarios (change PROPERTIES_FILE and PROCESSING_DELAY_MS, then restart):
 *
 *   Scenario A — Baseline (no lag):
 *     PROPERTIES_FILE    = "consumer-baseline.properties"
 *     PROCESSING_DELAY_MS = 0
 *     Expected: lag ≈ 0, consumer keeps up with the producer.
 *
 *   Scenario B — Moderate lag:
 *     PROPERTIES_FILE    = "consumer-baseline.properties"
 *     PROCESSING_DELAY_MS = 200
 *     Expected: lag grows steadily because the consumer processes only ~5 records/sec
 *     while the producer emits ~125 records/sec across 2 partitions.
 *
 *   Scenario C — Rebalance trigger (data loss / duplicates):
 *     PROPERTIES_FILE    = "consumer-low-maxpoll.properties"  (max.poll.interval.ms=5000)
 *     PROCESSING_DELAY_MS = 8000
 *     Expected: after a few polls the total time between two consecutive poll() calls
 *     exceeds 5 000 ms, Kafka removes the consumer from the group, triggers a rebalance,
 *     and re-delivers uncommitted messages — resulting in duplicate eventIDs in the output.
 */
public class SlowConsumer {

    // ── Experiment knobs ────────────────────────────────────────────────────
    private static final String PROPERTIES_FILE     = "consumer-baseline.properties";
    private static final long   PROCESSING_DELAY_MS = 0;
    // ────────────────────────────────────────────────────────────────────────

    public static void main(String[] args) throws IOException, InterruptedException {

        Properties props = loadProperties(PROPERTIES_FILE);

        try (KafkaConsumer<String, Object> consumer = new KafkaConsumer<>(props)) {

            consumer.subscribe(Collections.singletonList("gaze-events"));

            System.out.printf("[SlowConsumer] Started | properties=%s | delay=%dms%n",
                    PROPERTIES_FILE, PROCESSING_DELAY_MS);
            System.out.println("[SlowConsumer] max.poll.interval.ms = "
                    + props.getProperty("max.poll.interval.ms", "300000 (default)"));

            while (true) {
                ConsumerRecords<String, Object> records = consumer.poll(Duration.ofMillis(100));

                for (ConsumerRecord<String, Object> record : records) {
                    LinkedHashMap<?, ?> gaze = (LinkedHashMap<?, ?>) record.value();

                    System.out.printf(
                            "[SlowConsumer] partition=%d offset=%d eventID=%s x=%s y=%s pupil=%s%n",
                            record.partition(),
                            record.offset(),
                            gaze.get("eventID"),
                            gaze.get("xPosition"),
                            gaze.get("yPosition"),
                            gaze.get("pupilSize"));

                    if (PROCESSING_DELAY_MS > 0) {
                        Thread.sleep(PROCESSING_DELAY_MS);
                    }
                }
            }
        }
    }

    private static Properties loadProperties(String filename) throws IOException {
        Properties props = new Properties();
        try (InputStream in = Resources.getResource(filename).openStream()) {
            props.load(in);
        }
        return props;
    }
}
