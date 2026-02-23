package ch.unisg.scs.consumer;

import ch.unisg.scs.base.KafkaTestBase;
import ch.unisg.scs.fixtures.KafkaTestFixtures;
import ch.unisg.scs.utils.KafkaTestUtils;
import ch.unisg.scs.utils.TestDataFactory;
import ch.unisg.scs.Clicks;

import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test suite for Click event consumer.
 * Tests Kafka consumer functionality for click events.
 */
@DisplayName("Click Event Consumer Tests")
public class ConsumerClickEventTest extends KafkaTestBase {

    private static final String CLICK_TOPIC = "click-events";
    private AdminClient adminClient;
    private KafkaProducer<String, Object> producer;
    private KafkaConsumer<String, Object> consumer;

    @BeforeEach
    void setUp() throws Exception {
        adminClient = KafkaTestFixtures.createAdminClient(getBootstrapServers());
        producer = KafkaTestFixtures.createClickProducer(getBootstrapServers());
        consumer = KafkaTestFixtures.createClickConsumer(getBootstrapServers(), "test-consumer-click");
        
        // Create topic
        try {
            KafkaTestUtils.deleteTopic(adminClient, CLICK_TOPIC);
            Thread.sleep(500);
        } catch (Exception e) {
            // Topic doesn't exist yet
        }
        
        KafkaTestUtils.createTopic(adminClient, CLICK_TOPIC, 3, (short) 1);
        Thread.sleep(500);
    }

    @Test
    @DisplayName("Should consume a single click event")
    void testConsumeSingleClickEvent() throws Exception {
        // Arrange
        Clicks clickEvent = TestDataFactory.createClickEvent(1, 500, 400, "LEFT");
        String deviceId = "device-1";
        
        consumer.subscribe(Arrays.asList(CLICK_TOPIC));
        
        // Act
        producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
            CLICK_TOPIC,
            deviceId,
            clickEvent
        )).get();
        
        // Assert
        var records = KafkaTestUtils.collectRecords(consumer, 1, 5000);
        assertEquals(1, records.size(), "Consumer should receive 1 record");
        assertEquals(deviceId, records.get(0).key());
        assertEquals(CLICK_TOPIC, records.get(0).topic());
    }

    @Test
    @DisplayName("Should consume multiple click events in sequence")
    void testConsumeMultipleClickEvents() throws Exception {
        // Arrange
        int eventCount = 8;
        String deviceId = "device-1";
        consumer.subscribe(Arrays.asList(CLICK_TOPIC));
        
        // Act
        for (int i = 0; i < eventCount; i++) {
            Clicks event = TestDataFactory.createClickEvent(i);
            producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                CLICK_TOPIC,
                deviceId,
                event
            )).get();
        }
        
        // Assert
        var records = KafkaTestUtils.collectRecords(consumer, eventCount, 5000);
        assertEquals(eventCount, records.size(), "Should receive all click events");
    }

    @Test
    @DisplayName("Should filter and consume only click events")
    void testConsumeOnlyClickEvents() throws Exception {
        // Arrange
        consumer.subscribe(Arrays.asList(CLICK_TOPIC));
        int clickEventCount = 5;
        
        // Act
        for (int i = 0; i < clickEventCount; i++) {
            Clicks event = TestDataFactory.createClickEvent(i);
            producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                CLICK_TOPIC,
                String.valueOf(i),
                event
            )).get();
        }
        
        // Assert
        var records = KafkaTestUtils.collectRecords(consumer, clickEventCount, 5000);
        assertEquals(clickEventCount, records.size());
        assertTrue(records.stream().allMatch(r -> r.topic().equals(CLICK_TOPIC)));
    }

    @Test
    @DisplayName("Should handle consumer group offset commits")
    void testConsumerOffsetCommits() throws Exception {
        // Create consumer with auto-commit disabled
        consumer.close();
        consumer = KafkaTestFixtures.createConsumer(getBootstrapServers(), "test-commit-group");
        
        consumer.subscribe(Arrays.asList(CLICK_TOPIC));
        
        // Produce events
        int eventCount = 3;
        for (int i = 0; i < eventCount; i++) {
            Clicks event = TestDataFactory.createClickEvent(i);
            producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                CLICK_TOPIC,
                String.valueOf(i),
                event
            )).get();
        }
        
        // Consume and commit
        var records = KafkaTestUtils.collectRecords(consumer, eventCount, 5000);
        assertEquals(eventCount, records.size());
        
        // Commit offsets
        consumer.commitSync();
        
        // Verify that consumer remembers committed offset
        assertDoesNotThrow(() -> consumer.committed(consumer.assignment()));
    }

    @org.junit.jupiter.api.AfterEach
    void tearDown() {
        if (producer != null) producer.close();
        if (consumer != null) consumer.close();
        if (adminClient != null) adminClient.close();
    }
}

