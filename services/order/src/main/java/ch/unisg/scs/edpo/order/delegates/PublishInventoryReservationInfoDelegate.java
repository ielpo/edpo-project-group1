package ch.unisg.scs.edpo.order.delegates;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.UUID;

@Component("publishInventoryReservationInfoDelegate")
public class PublishInventoryReservationInfoDelegate implements JavaDelegate {

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;
    private final String infoTopic;

    public PublishInventoryReservationInfoDelegate(
            KafkaTemplate<String, String> kafkaTemplate,
            ObjectMapper objectMapper,
            @Value("${kafka.topics.info:info.v1}") String infoTopic) {
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
        this.infoTopic = infoTopic;
    }

    @Override
    public void execute(DelegateExecution execution) {
        String orderId = getOrderId(execution);
        String correlationId = UUID.randomUUID().toString();
        String message = getMessage(execution);

        Map<String, Object> payload = Map.of(
                "message", message,
                "orderId", orderId,
                "correlationId", correlationId
        );

        try {
            String serialized = objectMapper.writeValueAsString(payload);
            kafkaTemplate.send(infoTopic, orderId, serialized);
            execution.setVariable("correlationId", correlationId);
        } catch (Exception e) {
            // Best-effort notification: process should continue on business-failure branch.
            execution.setVariable("infoPublishError", e.getMessage());
        }
    }

    private String getOrderId(DelegateExecution execution) {
        Object value = execution.getVariable("orderId");
        return value == null ? "unknown-order" : value.toString();
    }

    private String getMessage(DelegateExecution execution) {
        Object value = execution.getVariable("inventoryReservationErrorMessage");
        if (value != null && !value.toString().isBlank()) {
            return "Reservation not possible: " + value;
        }
        return "Reservation not possible due to insufficient inventory.";
    }
}
