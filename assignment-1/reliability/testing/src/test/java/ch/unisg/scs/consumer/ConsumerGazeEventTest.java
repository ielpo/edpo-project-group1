package ch.unisg.scs.consumer;

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

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test suite for Gaze event consumer.
 * Tests Kafka consumer functionality for gaze events.
 */
@DisplayName("Gaze Event Consumer Tests")
public class ConsumerGazeEventTest extends KafkaTestBase {

    private static final String GAZE_TOPIC = "gaze-events";
    private AdminClient adminClient;
    private KafkaProducer<String, Object> producer;
    private KafkaConsumer<String, Object> consumer;

    @BeforeEach
    void setUp() throws Exception {
        adminClient = KafkaTestFixtures.createAdminClient(getBootstrapServers());
        producer = KafkaTestFixtures.createGazeProducer(getBootstrapServers());
        consumer = KafkaTestFixtures.createGazeConsumer(getBootstrapServers(), "test-consumer-gaze");
        
        // Create topic
        try {
            KafkaTestUtils.deleteTopic(adminClient, GAZE_TOPIC);
            Thread.sleep(500);
        } catch (Exception e) {
            // Topic doesn't exist yet
        }
        
        KafkaTestUtils.createTopic(adminClient, GAZE_TOPIC, 3, (short) 1);
        Thread.sleep(500);
    }

    @Test
    @DisplayName("Should consume a single gaze event")
    void testConsumeSingleGazeEvent() throws Exception {
        // Arrange
        Gaze gazeEvent = TestDataFactory.createGazeEvent(1, 100, 200);
        String deviceId = "device-1";
        
        consumer.subscribe(Arrays.asList(GAZE_TOPIC));
        
        // Act
        producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
            GAZE_TOPIC,
            deviceId,
            gazeEvent
        )).get();
        
        // Assert
        var records = KafkaTestUtils.collectRecords(consumer, 1, 5000);
        assertEquals(1, records.size(), "Consumer should receive 1 record");
        assertEquals(deviceId, records.get(0).key());
        assertEquals(GAZE_TOPIC, records.get(0).topic());
    }

    @Test
    @DisplayName("Should consume multiple gaze events in order")
    void testConsumeMultipleGazeEventsInOrder() throws Exception {
        // Arrange
        int eventCount = 10;
        String deviceId = "device-1";
        consumer.subscribe(Arrays.asList(GAZE_TOPIC));
        
        // Act - Produce events
        for (int i = 0; i < eventCount; i++) {
            Gaze event = TestDataFactory.createGazeEvent(i);
            producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                GAZE_TOPIC,
                deviceId,
                event
            )).get();
        }
        
        // Assert - Consume events
        var records = KafkaTestUtils.collectRecords(consumer, eventCount, 5000);
        assertEquals(eventCount, records.size(), "Consumer should receive all events");
        
        // Verify order within partition
        for (int i = 1; i < records.size(); i++) {
            assertTrue(
                records.get(i).offset() >= records.get(i - 1).offset(),
                "Records should maintain offset order"
            );
        }
    }

    @Test
    @DisplayName("Should handle consumer group rebalancing")
    void testConsumerGroupRebalancing() throws Exception {
        // Arrange
        String groupId = "test-rebalance-group";
        int eventCount = 5;
        consumer.close();
        consumer = KafkaTestFixtures.createGazeConsumer(getBootstrapServers(), groupId);
        
        // Act
        consumer.subscribe(Arrays.asList(GAZE_TOPIC));
        
        for (int i = 0; i < eventCount; i++) {
            Gaze event = TestDataFactory.createGazeEvent(i);
            producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                GAZE_TOPIC,
                String.valueOf(i % 3),
                event
            )).get();
        }
        
        // Assert
        var records = KafkaTestUtils.collectRecords(consumer, eventCount, 5000);
        assertEquals(eventCount, records.size());
    }

    @Test
    @DisplayName("Should consume events from multiple partitions")
    void testConsumeFromMultiplePartitions() throws Exception {
        // Arrange
        int eventsPerPartition = 3;
        consumer.subscribe(Arrays.asList(GAZE_TOPIC));
        
        // Act - Send events to different partitions
        for (int partition = 0; partition < 3; partition++) {
            for (int i = 0; i < eventsPerPartition; i++) {
                Gaze event = TestDataFactory.createGazeEvent(partition * eventsPerPartition + i);
                producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                    GAZE_TOPIC,
                    String.valueOf(partition),
                    event
                )).get();
            }
        }
        
        // Assert
        var records = KafkaTestUtils.collectRecords(consumer, eventsPerPartition * 3, 5000);
        assertEquals(eventsPerPartition * 3, records.size(), "Should receive events from all partitions");
    }

    @Test
    @DisplayName("Should handle consumer offset management")
    void testConsumerOffsetManagement() throws Exception {
        // Arrange
        consumer.subscribe(Arrays.asList(GAZE_TOPIC));
        
        // Produce initial events
        int initialEvents = 3;
        for (int i = 0; i < initialEvents; i++) {
            Gaze event = TestDataFactory.createGazeEvent(i);
            producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                GAZE_TOPIC,
                String.valueOf(i),
                event
            )).get();
        }
        
        // Act & Assert - Consume first batch
        var firstBatch = KafkaTestUtils.collectRecords(consumer, initialEvents, 5000);
        assertEquals(initialEvents, firstBatch.size());
        
        // Produce more events
        int moreEvents = 2;
        for (int i = initialEvents; i < initialEvents + moreEvents; i++) {
            Gaze event = TestDataFactory.createGazeEvent(i);
            producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                GAZE_TOPIC,
                String.valueOf(i),
                event
            )).get();
        }
        
        // Consume second batch
        var secondBatch = KafkaTestUtils.collectRecords(consumer, moreEvents, 5000);
        assertEquals(moreEvents, secondBatch.size());
    }

    @org.junit.jupiter.api.AfterEach
    void tearDown() {
        if (producer != null) producer.close();
        if (consumer != null) consumer.close();
        if (adminClient != null) adminClient.close();
    }
}

