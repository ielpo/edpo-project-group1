package ch.unisg.scs.edpo.kafkastreams.config;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

@Configuration
public class KafkaTopicConfig {

    @Value("${kafka.topics.distance-raw}")
    private String distanceRawTopic;

    @Value("${kafka.topics.color-raw}")
    private String colorRawTopic;

    @Value("${kafka.topics.block-detected}")
    private String blockDetectedTopic;

    @Value("${kafka.topics.inventory-blocks}")
    private String inventoryBlocksTopic;

    @Bean
    public NewTopic sensorDistanceRawTopic() {
        return TopicBuilder.name(distanceRawTopic).partitions(1).replicas(1).build();
    }

    @Bean
    public NewTopic sensorColorRawTopic() {
        return TopicBuilder.name(colorRawTopic).partitions(1).replicas(1).build();
    }

    @Bean
    public NewTopic blockDetectedTopic() {
        return TopicBuilder.name(blockDetectedTopic).partitions(1).replicas(1).build();
    }

    @Bean
    public NewTopic inventoryBlocksTopic() {
        return TopicBuilder.name(inventoryBlocksTopic).partitions(1).replicas(1).build();
    }
}
