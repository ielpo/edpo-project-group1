package ch.unisg.scs.producer;

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
 * Test suite for Click event producer.
 * Tests Kafka producer functionality for click events.
 */
@DisplayName("Click Event Producer Tests")
public class ProducerClickEventTest extends KafkaTestBase {

    private static final String CLICK_TOPIC = "click-events";
    private AdminClient adminClient;
    private KafkaProducer<String, Object> producer;
    private KafkaConsumer<String, Object> consumer;

    @BeforeEach
    void setUp() throws Exception {
        adminClient = KafkaTestFixtures.createAdminClient(getBootstrapServers());
        producer = KafkaTestFixtures.createClickProducer(getBootstrapServers());
        consumer = KafkaTestFixtures.createClickConsumer(getBootstrapServers(), "test-group-click");
        
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
    @DisplayName("Should successfully produce a single click event")
    void testProduceSingleClickEvent() throws Exception {
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
        assertEquals(1, records.size(), "Should receive exactly 1 record");
        assertTrue(KafkaTestUtils.hasKey(records.get(0), deviceId));
        assertTrue(KafkaTestUtils.hasTopic(records.get(0), CLICK_TOPIC));
    }

    @Test
    @DisplayName("Should produce multiple click events in sequence")
    void testProduceMultipleClickEvents() throws Exception {
        // Arrange
        int eventCount = 5;
        consumer.subscribe(Arrays.asList(CLICK_TOPIC));
        
        // Act
        for (int i = 0; i < eventCount; i++) {
            Clicks event = TestDataFactory.createClickEvent(i);
            producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                CLICK_TOPIC,
                String.valueOf(TestDataFactory.getRandomDeviceId()),
                event
            )).get();
        }
        
        // Assert
        var records = KafkaTestUtils.collectRecords(consumer, eventCount, 5000);
        assertEquals(eventCount, records.size(), "Should receive all " + eventCount + " records");
    }

    @Test
    @DisplayName("Should handle both LEFT and RIGHT click buttons")
    void testClickButtonTypes() throws Exception {
        // Arrange
        consumer.subscribe(Arrays.asList(CLICK_TOPIC));
        String[] buttonTypes = {"LEFT", "RIGHT"};
        
        // Act
        for (int i = 0; i < buttonTypes.length; i++) {
            Clicks event = TestDataFactory.createClickEvent(i, 500, 400, buttonTypes[i]);
            producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
                CLICK_TOPIC,
                String.valueOf(i),
                event
            )).get();
        }
        
        // Assert
        var records = KafkaTestUtils.collectRecords(consumer, 2, 5000);
        assertEquals(2, records.size(), "Should receive both button type events");
    }

    @Test
    @DisplayName("Should preserve click event data through production and consumption")
    void testClickEventDataIntegrity() throws Exception {
        // Arrange
        consumer.subscribe(Arrays.asList(CLICK_TOPIC));
        int eventId = 99;
        int xPos = 1024;
        int yPos = 768;
        String buttonType = "RIGHT";
        Clicks originalEvent = TestDataFactory.createClickEvent(eventId, xPos, yPos, buttonType);
        
        // Act
        producer.send(new org.apache.kafka.clients.producer.ProducerRecord<>(
            CLICK_TOPIC,
            "device-test",
            originalEvent
        )).get();
        
        // Assert
        var records = KafkaTestUtils.collectRecords(consumer, 1, 5000);
        assertEquals(1, records.size());
        assertNotNull(records.get(0).value(), "Record value should not be null");
    }

    @org.junit.jupiter.api.AfterEach
    void tearDown() {
        if (producer != null) producer.close();
        if (consumer != null) consumer.close();
        if (adminClient != null) adminClient.close();
    }
}

