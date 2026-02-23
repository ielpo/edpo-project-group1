package ch.unisg.scs.reliability;

import ch.unisg.scs.base.KafkaTestBase;
import ch.unisg.scs.fixtures.KafkaTestFixtures;
import ch.unisg.scs.utils.KafkaTestUtils;
import ch.unisg.scs.utils.TestDataFactory;
import ch.unisg.scs.Gaze;

import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.concurrent.ExecutionException;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Reliability test suite for Kafka producer and consumer.
 * Tests fault tolerance, data durability, and recovery scenarios.
 */
@DisplayName("Kafka Reliability Tests")
public class ReliabilityTest extends KafkaTestBase {

    private static final String TOPIC = "reliability-test-topic";
    private AdminClient adminClient;
    private KafkaProducer<String, Object> producer;
    private KafkaConsumer<String, Object> consumer;

    @BeforeEach
    void setUp() throws Exception {
        adminClient = KafkaTestFixtures.createAdminClient(getBootstrapServers());
        producer = KafkaTestFixtures.createProducer(getBootstrapServers());
        consumer = KafkaTestFixtures.createConsumer(getBootstrapServers(), "reliability-test-group");
        
        // Create topic
        try {
            KafkaTestUtils.deleteTopic(adminClient, TOPIC);
            Thread.sleep(500);
        } catch (Exception e) {
            // Topic doesn't exist yet
        }
        
        KafkaTestUtils.createTopic(adminClient, TOPIC, 3, (short) 1);
        Thread.sleep(500);
    }

    @Test
    @DisplayName("Should guarantee at-least-once delivery semantics")
    void testAtLeastOnceDelivery() throws Exception {
        // Arrange
        consumer.subscribe(Arrays.asList(TOPIC));
        int eventCount = 10;
        
        // Act
        for (int i = 0; i < eventCount; i++) {
            Gaze event = TestDataFactory.createGazeEvent(i);
            producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                TOPIC,
                String.valueOf(i),
                event
            )).get();
        }
        
        // Assert
        var records = KafkaTestUtils.collectRecords(consumer, eventCount, 5000);
        assertTrue(records.size() >= eventCount, "Should receive at least all produced events");
    }

    @Test
    @DisplayName("Should recover from consumer group failures")
    void testConsumerGroupRecovery() throws Exception {
        // Arrange & Act
        consumer.subscribe(Arrays.asList(TOPIC));
        
        // Produce events
        int eventCount = 5;
        for (int i = 0; i < eventCount; i++) {
            Gaze event = TestDataFactory.createGazeEvent(i);
            producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                TOPIC,
                String.valueOf(i),
                event
            )).get();
        }
        
        // Consume and commit
        var records = KafkaTestUtils.collectRecords(consumer, eventCount, 5000);
        consumer.commitSync();
        
        // Assert
        assertEquals(eventCount, records.size());
        
        // Simulate recovery: seek to beginning and verify we can read again
        consumer.seekToBeginning(consumer.assignment());
        var recoveredRecords = KafkaTestUtils.collectRecords(consumer, eventCount, 5000);
        assertEquals(eventCount, recoveredRecords.size());
    }

    @Test
    @DisplayName("Should handle producer retries on transient failures")
    void testProducerRetries() throws Exception {
        // Arrange
        consumer.subscribe(Arrays.asList(TOPIC));
        int eventCount = 3;
        
        // Act - Send events (producer will retry if needed)
        for (int i = 0; i < eventCount; i++) {
            Gaze event = TestDataFactory.createGazeEvent(i);
            try {
                producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                    TOPIC,
                    String.valueOf(i),
                    event
                )).get();
            } catch (ExecutionException e) {
                fail("Producer should not fail for valid messages");
            }
        }
        
        // Assert
        var records = KafkaTestUtils.collectRecords(consumer, eventCount, 5000);
        assertEquals(eventCount, records.size(), "All events should be persisted despite retries");
    }

    @Test
    @DisplayName("Should handle consumer offset tracking across sessions")
    void testOffsetPersistence() throws Exception {
        // Arrange - First session
        consumer.subscribe(Arrays.asList(TOPIC));
        int firstBatchSize = 3;
        
        // Produce first batch
        for (int i = 0; i < firstBatchSize; i++) {
            Gaze event = TestDataFactory.createGazeEvent(i);
            producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                TOPIC,
                String.valueOf(i),
                event
            )).get();
        }
        
        // Consume and commit first batch
        var firstBatch = KafkaTestUtils.collectRecords(consumer, firstBatchSize, 5000);
        consumer.commitSync();
        assertEquals(firstBatchSize, firstBatch.size());
        
        // Close consumer (simulate session end)
        long firstBatchLastOffset = firstBatch.get(firstBatchSize - 1).offset();
        consumer.close();
        
        // Create new consumer with same group
        consumer = KafkaTestFixtures.createConsumer(getBootstrapServers(), "reliability-test-group");
        consumer.subscribe(Arrays.asList(TOPIC));
        
        // Produce second batch
        int secondBatchSize = 2;
        for (int i = firstBatchSize; i < firstBatchSize + secondBatchSize; i++) {
            Gaze event = TestDataFactory.createGazeEvent(i);
            producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                TOPIC,
                String.valueOf(i),
                event
            )).get();
        }
        
        // Assert - Consumer should only receive new messages
        var secondBatch = KafkaTestUtils.collectRecords(consumer, secondBatchSize, 5000);
        assertEquals(secondBatchSize, secondBatch.size(), "Consumer should resume from committed offset");
        assertTrue(
            secondBatch.get(0).offset() > firstBatchLastOffset,
            "Second batch should have offsets after first batch"
        );
    }

    @Test
    @DisplayName("Should preserve data durability")
    void testDataDurability() throws Exception {
        // Arrange
        consumer.subscribe(Arrays.asList(TOPIC));
        Gaze gazeEvent = TestDataFactory.createGazeEvent(99, 512, 384);
        String key = "durable-key";
        
        // Act - Send with acknowledgment
        producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
            TOPIC,
            key,
            gazeEvent
        )).get();
        
        // Assert - Event should be retrievable
        var records = KafkaTestUtils.collectRecords(consumer, 1, 5000);
        assertEquals(1, records.size());
        assertEquals(key, records.get(0).key());
        assertNotNull(records.get(0).value());
    }

    @org.junit.jupiter.api.AfterEach
    void tearDown() {
        if (producer != null) producer.close();
        if (consumer != null) consumer.close();
        if (adminClient != null) adminClient.close();
    }
}

