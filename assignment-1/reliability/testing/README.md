# Kafka Testing Suite

This module contains comprehensive automated tests for Kafka producer and consumer functionality using JUnit 5 and Testcontainers.

## Project Structure

```
testing/
├── src/test/java/ch/unisg/scs/
│   ├── base/
│   │   └── KafkaTestBase.java              # Base class for all Kafka tests
│   ├── producer/
│   │   ├── ProducerGazeEventTest.java      # Gaze event producer tests
│   │   └── ProducerClickEventTest.java     # Click event producer tests
│   ├── consumer/
│   │   ├── ConsumerGazeEventTest.java      # Gaze event consumer tests
│   │   └── ConsumerClickEventTest.java     # Click event consumer tests
│   ├── integration/
│   │   └── KafkaIntegrationTest.java       # End-to-end integration tests
│   ├── reliability/
│   │   └── ReliabilityTest.java            # Reliability and fault tolerance tests
│   └── utils/
│       ├── KafkaTestUtils.java             # Utility methods for Kafka operations
│       ├── TestDataFactory.java            # Factory for creating test data
│       └── KafkaTestFixtures.java          # Fixtures for Kafka client setup
└── pom.xml                                 # Maven configuration
```

## Test Categories

### 1. Producer Tests (`producer/`)

**ProducerGazeEventTest:**
- Single gaze event production
- Multiple gaze events in sequence
- Event partitioning based on device ID
- Data integrity preservation

**ProducerClickEventTest:**
- Single click event production
- Multiple click events in sequence
- Button type handling (LEFT/RIGHT)
- Data integrity preservation

### 2. Consumer Tests (`consumer/`)

**ConsumerGazeEventTest:**
- Single event consumption
- Multiple events in order
- Consumer group rebalancing
- Multi-partition consumption
- Offset management

**ConsumerClickEventTest:**
- Single event consumption
- Multiple event consumption
- Event filtering
- Offset commit handling

### 3. Integration Tests (`integration/`)

**KafkaIntegrationTest:**
- End-to-end gaze event flow
- End-to-end click event flow
- Mixed event types on separate topics
- Data consistency across producer-consumer cycle
- High-volume event streams
- Event ordering within partitions

### 4. Reliability Tests (`reliability/`)

**ReliabilityTest:**
- At-least-once delivery semantics
- Consumer group failure recovery
- Producer retry behavior
- Offset persistence across sessions
- Data durability

## Test Utilities

### KafkaTestUtils
Provides helper methods for:
- Topic creation and deletion
- Record polling and collection
- Record validation (key, topic, partition matching)

### TestDataFactory
Factory methods for creating:
- Gaze events (random or with specific coordinates)
- Click events (random or with specific parameters)
- Device IDs
- Random values

### KafkaTestFixtures
Fixtures for creating pre-configured:
- AdminClient
- Producers (generic, gaze, click)
- Consumers (generic, gaze, click, with/without auto-commit)

## Running the Tests

### Run all tests
```bash
mvn clean test
```

### Run specific test class
```bash
mvn test -Dtest=ProducerGazeEventTest
```

### Run specific test method
```bash
mvn test -Dtest=ProducerGazeEventTest#testProduceSingleGazeEvent
```

### Run tests by category
```bash
# Producer tests only
mvn test -Dtest=Producer*

# Consumer tests only
mvn test -Dtest=Consumer*

# Integration tests only
mvn test -Dtest=KafkaIntegrationTest

# Reliability tests only
mvn test -Dtest=ReliabilityTest
```

## Dependencies

- **JUnit 5**: Modern testing framework
- **Testcontainers**: Docker-based Kafka container management
- **Awaitility**: Asynchronous testing support (optional enhancement)
- **Kafka Clients**: Apache Kafka client libraries
- **Logback**: Logging for test visibility

## Key Features

### 1. Automatic Kafka Container Lifecycle
- Testcontainers manages Kafka startup and cleanup
- Each test gets a fresh, isolated Kafka instance
- No manual Docker commands needed

### 2. Comprehensive Test Coverage
- Producer functionality (single/multiple messages, partitioning)
- Consumer functionality (offset management, rebalancing)
- Integration scenarios (multiple topics, data consistency)
- Reliability scenarios (recovery, durability, retry logic)

### 3. Reusable Test Utilities
- Base class provides common setup
- Factory classes reduce boilerplate
- Utility methods for common Kafka operations

### 4. Flexible Test Data
- Factory methods for creating test events
- Support for random or specific values
- Easy to extend for new event types

## Writing New Tests

### Template for a new producer test
```java
@DisplayName("Description of test")
void testSomething() throws Exception {
    // Arrange
    consumer.subscribe(Arrays.asList(TOPIC));
    
    // Act
    producer.send(new ProducerRecord<>(
        TOPIC,
        key,
        value
    )).get();
    
    // Assert
    var records = KafkaTestUtils.collectRecords(consumer, 1, 5000);
    assertEquals(1, records.size());
}
```

### Template for a new consumer test
```java
@DisplayName("Description of test")
void testSomething() throws Exception {
    // Arrange
    consumer.subscribe(Arrays.asList(TOPIC));
    // Produce some messages first
    
    // Act & Assert
    var records = KafkaTestUtils.collectRecords(consumer, expectedCount, timeoutMs);
    assertEquals(expectedCount, records.size());
}
```

## Best Practices

1. **Use DisplayName annotations** for clear test descriptions
2. **Follow AAA pattern** (Arrange-Act-Assert)
3. **Use meaningful assertion messages**
4. **Clean up resources** in @AfterEach methods
5. **Isolate tests** - each test should be independent
6. **Use test data factory** instead of hardcoding values
7. **Test both happy path and edge cases**

## Troubleshooting

### Tests timeout
- Increase timeout values in `collectRecords()` calls
- Check Kafka container logs for errors

### Consumer doesn't receive messages
- Verify topic exists before producing
- Ensure consumer subscribes before checking for records
- Check auto.offset.reset setting

### Partition-related assertions fail
- Remember: partition = hash(key) % num_partitions
- Use same key for messages that should go to same partition

## Future Enhancements

- [ ] Add Awaitility for more elegant async testing
- [ ] Add performance/throughput tests
- [ ] Add failure injection tests (simulating broker failures)
- [ ] Add schema validation tests
- [ ] Add transactional message tests
- [ ] Add dead letter queue tests

