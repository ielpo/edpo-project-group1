package ch.unisg.scs.edpo.factory.adapters.out;

import ch.unisg.scs.edpo.factory.application.ports.out.EventPublisherPort;
import lombok.RequiredArgsConstructor;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@RequiredArgsConstructor
@Component
public class KafkaEventPublisherAdapter implements EventPublisherPort {

    private final KafkaTemplate<String, String> kafkaTemplate;

    @Override
    public void publish(String topic, String key, String payload) {
        kafkaTemplate.send(topic, key, payload);
    }
}
