package ch.unisg.scs.edpo.dashboard;

import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class KafkaEventConsumer {

    private final EventWebSocketHandler webSocketHandler;
    private final ObjectMapper objectMapper;

    public KafkaEventConsumer(EventWebSocketHandler webSocketHandler, ObjectMapper objectMapper) {
        this.webSocketHandler = webSocketHandler;
        this.objectMapper = objectMapper;
    }

    @KafkaListener(topics = {"info.v1", "error.v1", "order.complete.v1"}, groupId = "dashboard")
    public void consume(ConsumerRecord<String, String> record) {
        try {
            ObjectNode payload = (ObjectNode) objectMapper.readTree(record.value());
            payload.put("_topic", record.topic());
            webSocketHandler.broadcast(payload.toString());
        } catch (Exception e) {
            ObjectNode fallback = objectMapper.createObjectNode();
            fallback.put("message", record.value());
            fallback.put("_topic", record.topic());
            webSocketHandler.broadcast(fallback.toString());
        }
    }

}
