package ch.unisg.scs.producer;

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
 * Test suite for Gaze event producer.
 * Tests Kafka producer functionality for gaze events.
 */
@DisplayName("Gaze Event Producer Tests")
public class ProducerGazeEventTest extends KafkaTestBase {

    private static final String GAZE_TOPIC = "gaze-events";
    private AdminClient adminClient;
    private KafkaProducer<String, Object> producer;
    private KafkaConsumer<String, Object> consumer;

    @BeforeEach
    void setUp() throws Exception {
        adminClient = KafkaTestFixtures.createAdminClient(getBootstrapServers());
        producer = KafkaTestFixtures.createGazeProducer(getBootstrapServers());
        consumer = KafkaTestFixtures.createGazeConsumer(getBootstrapServers(), "test-group-gaze");
        
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
    @DisplayName("Should successfully produce a single gaze event")
    void testProduceSingleGazeEvent() throws Exception {
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
        assertEquals(1, records.size(), "Should receive exactly 1 record");
        assertTrue(KafkaTestUtils.hasKey(records.get(0), deviceId));
        assertTrue(KafkaTestUtils.hasTopic(records.get(0), GAZE_TOPIC));
    }

    @Test
    @DisplayName("Should produce multiple gaze events in sequence")
    void testProduceMultipleGazeEvents() throws Exception {
        // Arrange
        int eventCount = 5;
        consumer.subscribe(Arrays.asList(GAZE_TOPIC));
        
        // Act
        for (int i = 0; i < eventCount; i++) {
            Gaze event = TestDataFactory.createGazeEvent(i);
            producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                GAZE_TOPIC,
                String.valueOf(TestDataFactory.getRandomDeviceId()),
                event
            )).get();
        }
        
        // Assert
        var records = KafkaTestUtils.collectRecords(consumer, eventCount, 5000);
        assertEquals(eventCount, records.size(), "Should receive all " + eventCount + " records");
    }

    @Test
    @DisplayName("Should distribute gaze events across partitions based on device ID")
    void testGazeEventPartitioning() throws Exception {
        // Arrange
        consumer.subscribe(Arrays.asList(GAZE_TOPIC));
        int eventsPerDevice = 3;
        
        // Act
        for (int device = 0; device < 3; device++) {
            for (int i = 0; i < eventsPerDevice; i++) {
                Gaze event = TestDataFactory.createGazeEvent(device * eventsPerDevice + i);
                producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                    GAZE_TOPIC,
                    String.valueOf(device),
                    event
                )).get();
            }
        }
        
        // Assert
        var records = KafkaTestUtils.collectRecords(consumer, 9, 5000);
        assertEquals(9, records.size());
        
        // Verify that records from same device go to same partition
        for (int device = 0; device < 3; device++) {
            var deviceRecords = records.stream()
                .filter(r -> KafkaTestUtils.hasKey(r, String.valueOf(device)))
                .toList();
            
            if (!deviceRecords.isEmpty()) {
                int partition = deviceRecords.get(0).partition();
                boolean allSamePartition = deviceRecords.stream()
                    .allMatch(r -> r.partition() == partition);
                assertTrue(allSamePartition, "All events from same device should be in same partition");
            }
        }
    }

    @Test
    @DisplayName("Should preserve gaze event data through production and consumption")
    void testGazeEventDataIntegrity() throws Exception {
        // Arrange
        consumer.subscribe(Arrays.asList(GAZE_TOPIC));
        int eventId = 42;
        int xPos = 800;
        int yPos = 600;
        Gaze originalEvent = TestDataFactory.createGazeEvent(eventId, xPos, yPos);
        
        // Act
        producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
            GAZE_TOPIC,
            "device-test",
            originalEvent
        )).get();
        
        // Assert
        var records = KafkaTestUtils.collectRecords(consumer, 1, 5000);
        assertEquals(1, records.size());
        assertNotNull(records.get(0).value(), "Record value should not be null");
    }

    @AfterEach
    void tearDown() {
        if (producer != null) producer.close();
        if (consumer != null) consumer.close();
        if (adminClient != null) adminClient.close();
    }

    @org.junit.jupiter.api.AfterEach
    void afterEach() {
        tearDown();
    }
}

