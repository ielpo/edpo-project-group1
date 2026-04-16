# Exercise 1 - Fault Tolerance and Reliability

This application evaluates Kafka's fault tolerance and reliability under broker failures and different durability configurations.
The priority is to measure message loss and latency for producers.

### Steps
1. **Set up Kafka cluster configurations**:
    - Define clusters with varying replication factors (e.g., 1, 2, 3).
    - Configure `acks` settings (`all`, `1`, `0`) in [producer.properties](assignment-1/reliability/producer/src/main/resources/producer.properties).

3. **Test dropped messages and durability**:
    - Produce messages under different replication and `acks` settings.
    - Stop brokers to simulate failures and verify message durability and latency.

4. **Analyze results**:
    - Compare metrics (e.g., latency, message loss) across configurations.
    - Document findings on fault tolerance and durability.

## Test 1

### Goal
Observe failure of one broker in a triple redundant setup with one producer and one consumer.

### Setup

| Component   | Configuration        |
|-------------|----------------------|
| Brokers     | 3                    |
| Producers   | 1                    |
| Consumers   | 1                    |
| Topics      | 1                    |
| Partitions  | 1                    |
| Replication Factor | 3             |
| Acks        | all                  |

### Procedure
1. Startup of all components
2. Producer is sending messages
3. Consumer is receiving messages
3. Kill leader broker for partition
4. Measure:
    - Time until new leader is elected
    - Latency until producer can send messages
    - Messages lost

### Expectations
The producer needs to wait for a new leader to be available before messages can be sent.
The consumer does not receive events for a certain amount of time.

### Results


## Test 2

### Goal
Check if messages are dropped when using no ack and double replication.

