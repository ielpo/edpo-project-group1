package ch.unisg.scs.edpo.factory.adapters.out;

import ch.unisg.scs.edpo.factory.application.ports.out.EventPublisherPort;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public class KafkaEventPublisherAdapter implements EventPublisherPort {

    private final KafkaTemplate<String, String> kafkaTemplate;

    public KafkaEventPublisherAdapter(KafkaTemplate<String, String> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    @Override
    public void publish(String topic, String key, String payload) {
        kafkaTemplate.send(topic, key, payload);
    }
}
