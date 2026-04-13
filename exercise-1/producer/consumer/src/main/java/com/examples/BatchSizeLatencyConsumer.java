package com.examples;

import com.google.common.io.Resources;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;

import java.io.InputStream;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.UUID;

/**
 * Reads three topics and reports latency stats once each hits the target count.
 */
public class BatchSizeLatencyConsumer {

    // Adjust accordingly to producer configuration
    private static final List<String> TOPICS = Arrays.asList(
            "clicks-batch-16k-1",
            "clicks-batch-64k-1",
            "clicks-batch-128k-1"
    );

    private static final int DEFAULT_TARGET_PER_TOPIC = 100000;
    private static final Duration POLL_TIMEOUT = Duration.ofMillis(250);
    private static final Duration MAX_RUNTIME = Duration.ofMinutes(10);

    public static void main(String[] args) throws Exception {
        int targetPerTopic = args.length > 0 ? Integer.parseInt(args[0]) : DEFAULT_TARGET_PER_TOPIC;

        Properties props = loadBaseProperties();
        props.put("group.id", "latency-probe-" + UUID.randomUUID());
        props.put("auto.offset.reset", "earliest");

        Map<String, List<Long>> latencies = new HashMap<>();
        Map<String, Integer> counts = new HashMap<>();
        for (String topic : TOPICS) {
            latencies.put(topic, new ArrayList<>());
            counts.put(topic, 0);
        }

        System.out.printf("Starting consumer for topics %s, target %,d each.%n", TOPICS, targetPerTopic);

        long startMs = System.currentTimeMillis();

        try (KafkaConsumer<String, Object> consumer = new KafkaConsumer<>(props)) {
            consumer.subscribe(TOPICS);

            while (true) {
                if (System.currentTimeMillis() - startMs > MAX_RUNTIME.toMillis()) {
                    System.out.println("Reached max runtime; summarizing what was collected.");
                    break;
                }

                ConsumerRecords<String, Object> records = consumer.poll(POLL_TIMEOUT);
                if (records.isEmpty()) {
                    continue;
                }

                for (ConsumerRecord<String, Object> record : records) {
                    Long producedAt = extractTimestamp(record.value());
                    if (producedAt == null) {
                        continue;
                    }

                    long latency = System.currentTimeMillis() - producedAt;
                    latencies.get(record.topic()).add(latency);
                    counts.put(record.topic(), counts.get(record.topic()) + 1);

                    if (counts.get(record.topic()) % 5_000 == 0) {
                        System.out.printf("[%s] collected %,d messages%n", record.topic(), counts.get(record.topic()));
                    }
                }

                boolean allReachedTarget = counts.values().stream().allMatch(count -> count >= targetPerTopic);
                if (allReachedTarget) {
                    System.out.println("Reached target for all topics; summarizing and exiting.");
                    break;
                }
            }
        }

        printSummary(latencies, counts, targetPerTopic);
        System.out.println("Done.");
        System.exit(0);
    }

    private static void printSummary(Map<String, List<Long>> latencies, Map<String, Integer> counts, int targetPerTopic) {
        System.out.println("\nLatency summary (ms):");
        for (String topic : TOPICS) {
            List<Long> values = latencies.get(topic);
            if (values == null || values.isEmpty()) {
                System.out.printf("%s -> no data collected%n", topic);
                continue;
            }

            Collections.sort(values);

            long min = values.get(0);
            long max = values.get(values.size() - 1);
            double avg = values.stream().mapToLong(Long::longValue).average().orElse(0);
            long p50 = percentile(values, 0.50);
            long p95 = percentile(values, 0.95);
            long p99 = percentile(values, 0.99);

            System.out.printf("%s -> count: %,d/%d | min: %d | p50: %d | p95: %d | p99: %d | max: %d | avg: %.2f%n",
                    topic,
                    counts.getOrDefault(topic, 0),
                    targetPerTopic,
                    min,
                    p50,
                    p95,
                    p99,
                    max,
                    avg);
        }
    }

    private static long percentile(List<Long> sortedValues, double percentile) {
        if (sortedValues.isEmpty()) {
            return 0;
        }
        int index = (int) Math.ceil(percentile * sortedValues.size()) - 1;
        index = Math.max(0, Math.min(index, sortedValues.size() - 1));
        return sortedValues.get(index);
    }

    private static Long extractTimestamp(Object value) {
        if (!(value instanceof Map)) {
            return null;
        }
        Map<?, ?> payload = (Map<?, ?>) value;
        Object ts = payload.get("timestamp");
        if (ts == null) {
            return null;
        }
        try {
            return Long.parseLong(ts.toString());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static Properties loadBaseProperties() throws Exception {
        try (InputStream props = Resources.getResource("consumer.properties").openStream()) {
            Properties properties = new Properties();
            properties.load(props);
            return properties;
        }
    }
}
