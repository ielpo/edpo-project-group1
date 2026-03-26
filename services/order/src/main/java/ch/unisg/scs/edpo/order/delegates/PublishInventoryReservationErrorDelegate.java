package ch.unisg.scs.edpo.order.delegates;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.UUID;

@Component("publishInventoryReservationErrorDelegate")
public class PublishInventoryReservationErrorDelegate implements JavaDelegate {

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;
    private final String errorTopic;

    public PublishInventoryReservationErrorDelegate(
            KafkaTemplate<String, String> kafkaTemplate,
            ObjectMapper objectMapper,
            @Value("${kafka.topics.error:error.v1}") String errorTopic) {
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
        this.errorTopic = errorTopic;
    }

    @Override
    public void execute(DelegateExecution execution) {
        String orderId = getOrderId(execution);
        String correlationId = getOrCreateCorrelationId(execution);
        String message = getMessage(execution);

        Map<String, Object> payload = Map.of(
                "message", message,
                "orderId", orderId,
                "correlationId", correlationId
        );

        try {
            String serialized = objectMapper.writeValueAsString(payload);
            kafkaTemplate.send(errorTopic, "0", serialized);
            execution.setVariable("correlationId", correlationId);
        } catch (Exception e) {
            // Best-effort notification: process should continue on technical-failure branch.
            execution.setVariable("errorPublishError", e.getMessage());
        }
    }

    private String getOrderId(DelegateExecution execution) {
        Object value = execution.getVariable("orderId");
        return value == null ? "unknown-order" : value.toString();
    }

    private String getMessage(DelegateExecution execution) {
        Object value = execution.getVariable("inventoryReservationErrorMessage");
        if (value != null && !value.toString().isBlank()) {
            return "Inventory service unavailable: " + value;
        }
        return "Inventory service unavailable during reservation.";
    }

    private String getOrCreateCorrelationId(DelegateExecution execution) {
        Object value = execution.getVariable("correlationId");
        if (value != null && !value.toString().isBlank()) {
            return value.toString();
        }

        String correlationId = UUID.randomUUID().toString();
        execution.setVariable("correlationId", correlationId);
        return correlationId;
    }
}
