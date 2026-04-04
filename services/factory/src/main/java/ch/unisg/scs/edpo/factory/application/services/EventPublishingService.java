package ch.unisg.scs.edpo.factory.application.services;

import ch.unisg.scs.edpo.factory.application.ports.in.EventPublishingUseCase;
import ch.unisg.scs.edpo.factory.application.ports.in.PublishNotificationCommand;
import ch.unisg.scs.edpo.factory.application.ports.in.PublishResult;
import ch.unisg.scs.edpo.factory.application.ports.out.EventPublisherPort;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.UUID;

@Service
public class EventPublishingService implements EventPublishingUseCase {

    private final EventPublisherPort eventPublisherPort;
    private final ObjectMapper objectMapper;
    private final String errorTopic;

    public EventPublishingService(
            EventPublisherPort eventPublisherPort,
            ObjectMapper objectMapper,
            @Value("${kafka.topics.error:error.v1}") String errorTopic) {
        this.eventPublisherPort = eventPublisherPort;
        this.objectMapper = objectMapper;
        this.errorTopic = errorTopic;
    }

    @Override
    public PublishResult publishError(PublishNotificationCommand command) {
        String correlationId = resolveCorrelationId(command.correlationId());
        String orderId = command.orderId() == null || command.orderId().isBlank()
                ? "unknown-order"
                : command.orderId();
        try {
            Map<String, Object> payload = Map.of(
                    "message", command.message(),
                    "orderId", orderId,
                    "correlationId", correlationId
            );
            String serialized = objectMapper.writeValueAsString(payload);
            eventPublisherPort.publish(errorTopic, "0", serialized);
            return new PublishResult(correlationId, null);
        } catch (Exception e) {
            return new PublishResult(correlationId, e.getMessage());
        }
    }

    private String resolveCorrelationId(String existingCorrelationId) {
        if (existingCorrelationId != null && !existingCorrelationId.isBlank()) {
            return existingCorrelationId;
        }
        return UUID.randomUUID().toString();
    }
}
