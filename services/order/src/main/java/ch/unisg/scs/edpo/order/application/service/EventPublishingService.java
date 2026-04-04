package ch.unisg.scs.edpo.order.application.service;

import ch.unisg.scs.edpo.order.application.port.in.EventPublishingUseCase;
import ch.unisg.scs.edpo.order.application.port.in.PublishManufactureCommand;
import ch.unisg.scs.edpo.order.application.port.in.PublishNotificationCommand;
import ch.unisg.scs.edpo.order.application.port.in.PublishResult;
import ch.unisg.scs.edpo.order.application.port.out.EventPublisherPort;
import ch.unisg.scs.edpo.order.domain.ItemType;
import ch.unisg.scs.edpo.order.domain.OrderDto;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.UUID;

@Service
public class EventPublishingService implements EventPublishingUseCase {

    private final EventPublisherPort eventPublisherPort;
    private final ObjectMapper objectMapper;
    private final String manufactureTopic;
    private final String infoTopic;
    private final String errorTopic;

    public EventPublishingService(
            EventPublisherPort eventPublisherPort,
            ObjectMapper objectMapper,
            @Value("${kafka.topics.order-manufacture:order.manufacture.v1}") String manufactureTopic,
            @Value("${kafka.topics.info:info.v1}") String infoTopic,
            @Value("${kafka.topics.error:error.v1}") String errorTopic) {
        this.eventPublisherPort = eventPublisherPort;
        this.objectMapper = objectMapper;
        this.manufactureTopic = manufactureTopic;
        this.infoTopic = infoTopic;
        this.errorTopic = errorTopic;
    }

    @Override
    public PublishResult publishManufactureCommand(PublishManufactureCommand command) {
        String correlationId = resolveCorrelationId(command.correlationId());
        try {
            ItemType itemType = ItemType.valueOf(command.itemType());
            OrderDto orderDto = new OrderDto(command.orderId(), itemType);
            Map<String, Object> payload = Map.of("order", orderDto, "correlationId", correlationId);
            String serialized = objectMapper.writeValueAsString(payload);
            eventPublisherPort.publish(manufactureTopic, "0", serialized);
            return new PublishResult(correlationId, null);
        } catch (Exception e) {
            return new PublishResult(correlationId, e.getMessage());
        }
    }

    @Override
    public PublishResult publishInfo(PublishNotificationCommand command) {
        return publishNotification(infoTopic, command);
    }

    @Override
    public PublishResult publishError(PublishNotificationCommand command) {
        return publishNotification(errorTopic, command);
    }

    private PublishResult publishNotification(String topic, PublishNotificationCommand command) {
        String correlationId = resolveCorrelationId(command.correlationId());
        String orderId = command.orderId() == null || command.orderId().isBlank() ? "unknown-order" : command.orderId();
        try {
            Map<String, Object> payload = Map.of(
                    "message", command.message(),
                    "orderId", orderId,
                    "correlationId", correlationId
            );
            String serialized = objectMapper.writeValueAsString(payload);
            eventPublisherPort.publish(topic, "0", serialized);
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
