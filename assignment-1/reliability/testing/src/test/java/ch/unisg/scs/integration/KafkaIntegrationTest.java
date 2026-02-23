package ch.unisg.scs.integration;

import ch.unisg.scs.base.KafkaTestBase;
import ch.unisg.scs.fixtures.KafkaTestFixtures;
import ch.unisg.scs.utils.KafkaTestUtils;
import ch.unisg.scs.utils.TestDataFactory;
import ch.unisg.scs.Gaze;
import ch.unisg.scs.Clicks;

import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Integration test suite for end-to-end Kafka functionality.
 * Tests producer and consumer working together across multiple topics.
 */
@DisplayName("Kafka End-to-End Integration Tests")
public class KafkaIntegrationTest extends KafkaTestBase {

    private static final String GAZE_TOPIC = "gaze-events";
    private static final String CLICK_TOPIC = "click-events";
    
    private AdminClient adminClient;
    private KafkaProducer<String, Object> gazeProducer;
    private KafkaProducer<String, Object> clickProducer;
    private KafkaConsumer<String, Object> gazeConsumer;
    private KafkaConsumer<String, Object> clickConsumer;
    private KafkaConsumer<String, Object> multiTopicConsumer;

    @BeforeEach
    void setUp() throws Exception {
        adminClient = KafkaTestFixtures.createAdminClient(getBootstrapServers());
        gazeProducer = KafkaTestFixtures.createGazeProducer(getBootstrapServers());
        clickProducer = KafkaTestFixtures.createClickProducer(getBootstrapServers());
        gazeConsumer = KafkaTestFixtures.createGazeConsumer(getBootstrapServers(), "test-gaze-consumer");
        clickConsumer = KafkaTestFixtures.createClickConsumer(getBootstrapServers(), "test-click-consumer");
        multiTopicConsumer = KafkaTestFixtures.createConsumer(getBootstrapServers(), "test-multi-consumer");
        
        // Create topics
        try {
            KafkaTestUtils.deleteTopic(adminClient, GAZE_TOPIC);
            KafkaTestUtils.deleteTopic(adminClient, CLICK_TOPIC);
            Thread.sleep(500);
        } catch (Exception e) {
            // Topics don't exist yet
        }
        
        KafkaTestUtils.createTopic(adminClient, GAZE_TOPIC, 3, (short) 1);
        KafkaTestUtils.createTopic(adminClient, CLICK_TOPIC, 3, (short) 1);
        Thread.sleep(500);
    }

    @Test
    @DisplayName("Should produce and consume gaze events end-to-end")
    void testGazeEventEndToEnd() throws Exception {
        // Arrange
        int eventCount = 5;
        gazeConsumer.subscribe(Arrays.asList(GAZE_TOPIC));
        
        // Act - Produce gaze events
        for (int i = 0; i < eventCount; i++) {
            Gaze event = TestDataFactory.createGazeEvent(i);
            gazeProducer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                GAZE_TOPIC,
                String.valueOf(TestDataFactory.getRandomDeviceId()),
                event
            )).get();
        }
        
        // Assert - Consume gaze events
        var records = KafkaTestUtils.collectRecords(gazeConsumer, eventCount, 5000);
        assertEquals(eventCount, records.size(), "All gaze events should be consumed");
        assertTrue(records.stream().allMatch(r -> r.topic().equals(GAZE_TOPIC)));
    }

    @Test
    @DisplayName("Should produce and consume click events end-to-end")
    void testClickEventEndToEnd() throws Exception {
        // Arrange
        int eventCount = 5;
        clickConsumer.subscribe(Arrays.asList(CLICK_TOPIC));
        
        // Act - Produce click events
        for (int i = 0; i < eventCount; i++) {
            Clicks event = TestDataFactory.createClickEvent(i);
            clickProducer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                CLICK_TOPIC,
                String.valueOf(TestDataFactory.getRandomDeviceId()),
                event
            )).get();
        }
        
        // Assert - Consume click events
        var records = KafkaTestUtils.collectRecords(clickConsumer, eventCount, 5000);
        assertEquals(eventCount, records.size(), "All click events should be consumed");
        assertTrue(records.stream().allMatch(r -> r.topic().equals(CLICK_TOPIC)));
    }

    @Test
    @DisplayName("Should handle mixed gaze and click events on separate topics")
    void testMixedEventTypesOnSeparateTopics() throws Exception {
        // Arrange
        int gazeEventCount = 3;
        int clickEventCount = 2;
        multiTopicConsumer.subscribe(Arrays.asList(GAZE_TOPIC, CLICK_TOPIC));
        
        // Act - Produce mixed events
        for (int i = 0; i < gazeEventCount; i++) {
            Gaze event = TestDataFactory.createGazeEvent(i);
            gazeProducer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                GAZE_TOPIC,
                String.valueOf(i),
                event
            )).get();
        }
        
        for (int i = 0; i < clickEventCount; i++) {
            Clicks event = TestDataFactory.createClickEvent(i);
            clickProducer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                CLICK_TOPIC,
                String.valueOf(i),
                event
            )).get();
        }
        
        // Assert - Consume mixed events
        var allRecords = KafkaTestUtils.collectRecords(
            multiTopicConsumer, 
            gazeEventCount + clickEventCount, 
            5000
        );
        
        assertEquals(gazeEventCount + clickEventCount, allRecords.size());
        
        var gazeEvents = allRecords.stream()
            .filter(r -> r.topic().equals(GAZE_TOPIC))
            .collect(Collectors.toList());
        var clickEvents = allRecords.stream()
            .filter(r -> r.topic().equals(CLICK_TOPIC))
            .collect(Collectors.toList());
        
        assertEquals(gazeEventCount, gazeEvents.size());
        assertEquals(clickEventCount, clickEvents.size());
    }

    @Test
    @DisplayName("Should maintain data consistency across producer-consumer cycle")
    void testDataConsistency() throws Exception {
        // Arrange
        gazeConsumer.subscribe(Arrays.asList(GAZE_TOPIC));
        int xPos = 512;
        int yPos = 384;
        
        // Act
        Gaze originalGaze = TestDataFactory.createGazeEvent(1, xPos, yPos);
        gazeProducer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
            GAZE_TOPIC,
            "device-1",
            originalGaze
        )).get();
        
        // Assert
        var records = KafkaTestUtils.collectRecords(gazeConsumer, 1, 5000);
        assertEquals(1, records.size());
        assertNotNull(records.get(0).value());
    }

    @Test
    @DisplayName("Should handle high-volume event stream")
    void testHighVolumeEventStream() throws Exception {
        // Arrange
        int eventCount = 100;
        gazeConsumer.subscribe(Arrays.asList(GAZE_TOPIC));
        
        // Act
        for (int i = 0; i < eventCount; i++) {
            Gaze event = TestDataFactory.createGazeEvent(i);
            gazeProducer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                GAZE_TOPIC,
                String.valueOf(i % 3),
                event
            )).get();
        }
        
        // Assert
        var records = KafkaTestUtils.collectRecords(gazeConsumer, eventCount, 10000);
        assertEquals(eventCount, records.size(), "All high-volume events should be consumed");
    }

    @Test
    @DisplayName("Should preserve event ordering within partitions")
    void testEventOrderingWithinPartitions() throws Exception {
        // Arrange
        int deviceId = 1;
        int eventCount = 10;
        gazeConsumer.subscribe(Arrays.asList(GAZE_TOPIC));
        
        // Act - Send all events with same key (same partition)
        for (int i = 0; i < eventCount; i++) {
            Gaze event = TestDataFactory.createGazeEvent(i);
            gazeProducer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                GAZE_TOPIC,
                String.valueOf(deviceId),
                event
            )).get();
        }
        
        // Assert
        var records = KafkaTestUtils.collectRecords(gazeConsumer, eventCount, 5000);
        assertEquals(eventCount, records.size());
        
        // Verify all records are from same partition
        long firstPartition = records.get(0).partition();
        assertTrue(records.stream().allMatch(r -> r.partition() == firstPartition));
        
        // Verify offset ordering
        for (int i = 1; i < records.size(); i++) {
            assertTrue(
                records.get(i).offset() > records.get(i - 1).offset(),
                "Offsets should increase monotonically"
            );
        }
    }

    @org.junit.jupiter.api.AfterEach
    void tearDown() {
        if (gazeProducer != null) gazeProducer.close();
        if (clickProducer != null) clickProducer.close();
        if (gazeConsumer != null) gazeConsumer.close();
        if (clickConsumer != null) clickConsumer.close();
        if (multiTopicConsumer != null) multiTopicConsumer.close();
        if (adminClient != null) adminClient.close();
    }
}

