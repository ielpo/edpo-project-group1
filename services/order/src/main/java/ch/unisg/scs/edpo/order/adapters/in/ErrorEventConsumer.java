package ch.unisg.scs.edpo.order.adapters.in;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.operaton.bpm.engine.MismatchingMessageCorrelationException;
import org.operaton.bpm.engine.RuntimeService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class ErrorEventConsumer {

    private static final Logger LOG = LoggerFactory.getLogger(ErrorEventConsumer.class);

    private final RuntimeService runtimeService;
    private final ObjectMapper objectMapper;

    public ErrorEventConsumer(RuntimeService runtimeService, ObjectMapper objectMapper) {
        this.runtimeService = runtimeService;
        this.objectMapper = objectMapper;
    }

    @KafkaListener(topics = "${kafka.topics.error:error.v1}")
    public void onErrorEvent(String payload) {
        try {
            JsonNode root = objectMapper.readTree(payload);
            String orderId = textValue(root, "orderId");
            String correlationId = textValue(root, "correlationId");

            if (orderId == null || correlationId == null) {
                LOG.warn("Skipping error.v1 event with missing orderId/correlationId: {}", payload);
                return;
            }

            runtimeService.createMessageCorrelation("error.v1")
                    .processInstanceVariableEquals("orderId", orderId)
                    .processInstanceVariableEquals("correlationId", correlationId)
                    .setVariable("factoryErrorOrderId", orderId)
                    .setVariable("factoryErrorCorrelationId", correlationId)
                    .correlate();

            LOG.info("Correlated error.v1 for orderId={} correlationId={}", orderId, correlationId);
        } catch (MismatchingMessageCorrelationException e) {
            LOG.warn("No matching process instance for error.v1 payload: {}", payload);
        } catch (Exception e) {
            LOG.error("Failed to handle error.v1 payload: {}", payload, e);
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
