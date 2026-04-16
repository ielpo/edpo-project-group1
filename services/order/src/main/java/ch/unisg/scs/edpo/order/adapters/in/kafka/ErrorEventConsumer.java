package ch.unisg.scs.edpo.order.adapters.in.kafka;

import ch.unisg.scs.edpo.order.application.port.in.CorrelateEventCommand;
import ch.unisg.scs.edpo.order.application.port.in.EventCorrelationUseCase;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class ErrorEventConsumer {
    private final EventCorrelationUseCase eventCorrelationUseCase;
    private final ObjectMapper objectMapper;

    public ErrorEventConsumer(EventCorrelationUseCase eventCorrelationUseCase, ObjectMapper objectMapper) {
        this.eventCorrelationUseCase = eventCorrelationUseCase;
        this.objectMapper = objectMapper;
    }

    @KafkaListener(topics = "${kafka.topics.error:error.v1}")
    public void onErrorEvent(String payload) {
        try {
            JsonNode root = objectMapper.readTree(payload);
            String orderId = textValue(root, "orderId");
            String correlationId = textValue(root, "correlationId");

            boolean correlated = eventCorrelationUseCase.correlateError(
                    new CorrelateEventCommand(orderId, correlationId)
            );

            if (!correlated) {
                log.debug("No matching process instance for error.v1 payload: {}", payload);
                return;
            }
            log.info("Correlated error.v1 for orderId={} correlationId={}", orderId, correlationId);
        } catch (Exception e) {
            log.error("Failed to handle error.v1 payload: {}", payload, e);
        }
    }

    private String textValue(JsonNode root, String field) {
        JsonNode node = root.get(field);
        if (node == null || node.isNull()) {
            return null;
        }
        String value = node.asText();
        return value == null || value.isBlank() ? null : value;
    }
}
