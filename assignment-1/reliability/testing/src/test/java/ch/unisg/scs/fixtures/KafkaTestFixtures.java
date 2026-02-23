package ch.unisg.scs.fixtures;

import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.producer.KafkaProducer;

import java.util.Properties;

/**
 * Fixtures for creating Kafka clients with test configurations.
 */
public class KafkaTestFixtures {

    /**
     * Create a Kafka admin client.
     * @param bootstrapServers bootstrap servers
     * @return configured AdminClient
     */
    public static AdminClient createAdminClient(String bootstrapServers) {
        Properties properties = new Properties();
        properties.put("bootstrap.servers", bootstrapServers);
        return AdminClient.create(properties);
    }

    /**
     * Create a Kafka producer for string keys and object values.
     * @param bootstrapServers bootstrap servers
     * @return configured KafkaProducer
     */
    public static KafkaProducer<String, Object> createProducer(String bootstrapServers) {
        Properties properties = new Properties();
        properties.put("bootstrap.servers", bootstrapServers);
        properties.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
        properties.put("value.serializer", "ch.unisg.scs.JavaSerializer");
        properties.put("acks", "all");
        properties.put("retries", 3);
        
        return new KafkaProducer<>(properties);
    }

    /**
     * Create a Kafka consumer for string keys and object values.
     * @param bootstrapServers bootstrap servers
     * @param groupId consumer group ID
     * @return configured KafkaConsumer
     */
    public static KafkaConsumer<String, Object> createConsumer(String bootstrapServers, String groupId) {
        Properties properties = new Properties();
        properties.put("bootstrap.servers", bootstrapServers);
        properties.put("group.id", groupId);
        properties.put("key.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
        properties.put("value.deserializer", "ch.unisg.scs.JavaDeserializer");
        properties.put("auto.offset.reset", "earliest");
        properties.put("enable.auto.commit", "false");
        
        return new KafkaConsumer<>(properties);
    }

    /**
     * Create a Kafka consumer with auto-commit enabled.
     * @param bootstrapServers bootstrap servers
     * @param groupId consumer group ID
     * @return configured KafkaConsumer
     */
    public static KafkaConsumer<String, Object> createConsumerAutoCommit(String bootstrapServers, String groupId) {
        Properties properties = new Properties();
        properties.put("bootstrap.servers", bootstrapServers);
        properties.put("group.id", groupId);
        properties.put("key.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
        properties.put("value.deserializer", "ch.unisg.scs.JavaDeserializer");
        properties.put("auto.offset.reset", "earliest");
        properties.put("enable.auto.commit", "true");
        properties.put("auto.commit.interval.ms", "1000");
        
        return new KafkaConsumer<>(properties);
    }

    /**
     * Create a Kafka producer for Gaze events.
     * @param bootstrapServers bootstrap servers
     * @return configured KafkaProducer
     */
    public static KafkaProducer<String, Object> createGazeProducer(String bootstrapServers) {
        return createProducer(bootstrapServers);
    }

    /**
     * Create a Kafka producer for Click events.
     * @param bootstrapServers bootstrap servers
     * @return configured KafkaProducer
     */
    public static KafkaProducer<String, Object> createClickProducer(String bootstrapServers) {
        return createProducer(bootstrapServers);
    }

    /**
     * Create a Kafka consumer for gaze-events topic.
     * @param bootstrapServers bootstrap servers
     * @param groupId consumer group ID
     * @return configured KafkaConsumer
     */
    public static KafkaConsumer<String, Object> createGazeConsumer(String bootstrapServers, String groupId) {
        return createConsumer(bootstrapServers, groupId);
    }

    /**
     * Create a Kafka consumer for click-events topic.
     * @param bootstrapServers bootstrap servers
     * @param groupId consumer group ID
     * @return configured KafkaConsumer
     */
    public static KafkaConsumer<String, Object> createClickConsumer(String bootstrapServers, String groupId) {
        return createConsumer(bootstrapServers, groupId);
    }
}

