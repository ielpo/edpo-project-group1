package com.examples;

import com.data.Clicks;
import com.google.common.io.Resources;
import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.DeleteTopicsResult;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;

import java.io.InputStream;
import java.time.Duration;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Properties;
import java.util.UUID;

/**
 * Sends a fixed number of messages for three batch/linger variants and prints simple throughput logs.
 */
public class BatchSizeExperimentProducer {

    private record Scenario(String name, String topic, int batchSize, int lingerMs) { }

    // Use a different topic to ensure clean comparisons
    private static final List<Scenario> SCENARIOS = Arrays.asList(
            new Scenario("16KB-100ms", "clicks-batch-16k-1", 16_384, 100), // default linger value
            new Scenario("64KB-100ms", "clicks-batch-64k-1", 65_536, 100),
            new Scenario("128KB-100ms", "clicks-batch-128k-1", 131_072, 100)

            // new Scenario("16KB-100ms", "clicks-batch-16k-6", 16_384, 100),
            // new Scenario("64KB-100ms", "clicks-batch-64k-6", 65_536, 100),
            // new Scenario("128KB-100ms", "clicks-batch-128k-6", 131_072, 100)
    );

    private static final int MESSAGE_COUNT = 100000;
    private static final int PARTITIONS = 3;
    private static final short REPLICATION = 1;

    public static void main(String[] args) throws Exception {
        Properties baseProps = loadBaseProperties();
        cleanTopics(baseProps);

        for (Scenario scenario : SCENARIOS) {
            runScenario(baseProps, scenario);
        }
    }

    private static void runScenario(Properties baseProps, Scenario scenario) throws Exception {
        Properties props = new Properties();
        props.putAll(baseProps);
        props.put("batch.size", scenario.batchSize());
        props.put("linger.ms", scenario.lingerMs());
        props.put("client.id", "batch-exp-" + scenario.name() + "-" + UUID.randomUUID());

        System.out.printf("[%s] topic=%s batch.size=%d linger.ms=%d sending %,d messages...%n",
                scenario.name(), scenario.topic(), scenario.batchSize(), scenario.lingerMs(), MESSAGE_COUNT);

        try (KafkaProducer<String, Clicks> producer = new KafkaProducer<>(props)) {
            long startNs = System.nanoTime();

            for (int i = 0; i < MESSAGE_COUNT; i++) {

                // For more realistic timing, we added a small random sleep here to investigate linger.ms impacts
                /*
                try {
                    Thread.sleep(getRandomNumber(0, 2));
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                */

                Clicks clickEvent = new Clicks(
                        i,
                        System.currentTimeMillis(),
                        getRandomNumber(0, 1920),
                        getRandomNumber(0, 1080),
                        "EL" + getRandomNumber(1, 20)
                );

                producer.send(new ProducerRecord<>(scenario.topic(), clickEvent));

                if ((i + 1) % 5_000 == 0) {
                    System.out.printf("[%s] sent %,d/%d%n", scenario.name(), i + 1, MESSAGE_COUNT);
                }
            }

            producer.flush();
            long elapsedMs = Duration.ofNanos(System.nanoTime() - startNs).toMillis();
            double throughput = (MESSAGE_COUNT * 1000.0) / Math.max(1, elapsedMs);
            System.out.printf("[%s] complete: %,d msgs in %d ms (%.2f msg/s)%n",
                    scenario.name(), MESSAGE_COUNT, elapsedMs, throughput);
        }
    }

    private static void cleanTopics(Properties props) throws Exception {
        try (AdminClient admin = AdminClient.create(props)) {
            // Delete if they exist (because of the earlier consumer startup, they are likely to exist)
            for (Scenario scenario : SCENARIOS) {
                deleteTopic(scenario.topic(), admin);
            }
            // Small wait to let deletions settle
            Thread.sleep(800);
            // Recreate topics (tolerate if they still exist)
            for (Scenario scenario : SCENARIOS) {
                NewTopic topic = new NewTopic(scenario.topic(), PARTITIONS, REPLICATION);
                try {
                    admin.createTopics(Collections.singleton(topic)).all().get();
                    System.out.printf("Created topic %s%n", scenario.topic());
                } catch (Exception e) {
                    System.out.printf(
                            "Failed to create topic %s%nException: %s%nCause: %s%n",
                            scenario.topic(),
                            e,
                            e.getCause()
                    );
                    // e.printStackTrace();
                }
            }
        }
    }

    /*
    Delete topic
     */
    private static void deleteTopic(String topicName, AdminClient client) {
        try {
            DeleteTopicsResult deleteTopicsResult = client.deleteTopics(Collections.singleton(topicName));
            while (!deleteTopicsResult.all().isDone()) {
                // wait
            }
        } catch (Exception ignored) {
        }
    }

    private static Properties loadBaseProperties() throws Exception {
        try (InputStream props = Resources.getResource("producer.properties").openStream()) {
            Properties properties = new Properties();
            properties.load(props);
            return properties;
        }
    }

    private static int getRandomNumber(int min, int max) {
        return (int) ((Math.random() * (max - min)) + min);
    }
}
