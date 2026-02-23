package ch.unisg.scs.utils;

import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.CreateTopicsResult;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;

import java.time.Duration;
import java.util.*;
import java.util.concurrent.ExecutionException;

/**
 * Utility class for Kafka testing operations.
 */
public class KafkaTestUtils {

    /**
     * Create a Kafka topic with the specified configuration.
     * @param adminClient Kafka admin client
     * @param topicName topic name
     * @param partitions number of partitions
     * @param replicationFactor replication factor
     * @throws ExecutionException if topic creation fails
     * @throws InterruptedException if thread is interrupted
     */
    public static void createTopic(AdminClient adminClient, String topicName, 
                                  int partitions, short replicationFactor) 
            throws ExecutionException, InterruptedException {
        NewTopic newTopic = new NewTopic(topicName, partitions, replicationFactor);
        CreateTopicsResult result = adminClient.createTopics(Collections.singleton(newTopic));
        result.all().get();
    }

    /**
     * Delete a Kafka topic.
     * @param adminClient Kafka admin client
     * @param topicName topic name
     * @throws ExecutionException if topic deletion fails
     * @throws InterruptedException if thread is interrupted
     */
    public static void deleteTopic(AdminClient adminClient, String topicName) 
            throws ExecutionException, InterruptedException {
        adminClient.deleteTopics(Collections.singleton(topicName)).all().get();
    }

    /**
     * Poll consumer records from Kafka.
     * @param consumer Kafka consumer
     * @param timeoutMs timeout in milliseconds
     * @return consumer records
     */
    public static ConsumerRecords<String, Object> pollRecords(KafkaConsumer<String, Object> consumer, 
                                                              long timeoutMs) {
        return consumer.poll(Duration.ofMillis(timeoutMs));
    }

    /**
     * Collect all records from consumer within a timeout period.
     * @param consumer Kafka consumer
     * @param expectedCount expected number of records
     * @param timeoutMs total timeout in milliseconds
     * @return list of consumer records
     */
    public static List<ConsumerRecord<String, Object>> collectRecords(
            KafkaConsumer<String, Object> consumer, int expectedCount, long timeoutMs) {
        List<ConsumerRecord<String, Object>> records = new ArrayList<>();
        long startTime = System.currentTimeMillis();
        
        while (System.currentTimeMillis() - startTime < timeoutMs && records.size() < expectedCount) {
            ConsumerRecords<String, Object> polledRecords = consumer.poll(Duration.ofMillis(100));
            polledRecords.forEach(records::add);
        }
        
        return records;
    }

    /**
     * Verify that a record has a specific key.
     * @param record consumer record
     * @param expectedKey expected key
     * @return true if key matches
     */
    public static boolean hasKey(ConsumerRecord<String, Object> record, String expectedKey) {
        return record.key() != null && record.key().equals(expectedKey);
    }

    /**
     * Verify that a record has a specific topic.
     * @param record consumer record
     * @param expectedTopic expected topic
     * @return true if topic matches
     */
    public static boolean hasTopic(ConsumerRecord<String, Object> record, String expectedTopic) {
        return record.topic().equals(expectedTopic);
    }

    /**
     * Verify that a record has a specific partition.
     * @param record consumer record
     * @param expectedPartition expected partition
     * @return true if partition matches
     */
    public static boolean hasPartition(ConsumerRecord<String, Object> record, int expectedPartition) {
        return record.partition() == expectedPartition;
    }
}

