package ch.unisg.scs.base;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.testcontainers.containers.KafkaContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;

/**
 * Base class for all Kafka integration tests.
 * Manages Kafka container lifecycle using Testcontainers.
 */
@Testcontainers
public abstract class KafkaTestBase {

    @Container
    static KafkaContainer kafka = new KafkaContainer(
        DockerImageName.parse("confluentinc/cp-kafka:7.5.0")
    ).withReuse(false);

    /**
     * Get the bootstrap servers URL for connecting to Kafka.
     * @return bootstrap servers connection string
     */
    protected static String getBootstrapServers() {
        return kafka.getBootstrapServers();
    }

    /**
     * Get the Kafka container instance.
     * @return KafkaContainer instance
     */
    protected static KafkaContainer getKafkaContainer() {
        return kafka;
    }
}

