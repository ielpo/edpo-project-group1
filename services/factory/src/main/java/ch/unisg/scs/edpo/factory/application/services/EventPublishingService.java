package ch.unisg.scs.edpo.factory.application.services;

import ch.unisg.scs.edpo.factory.application.ports.in.EventPublishingUseCase;
import ch.unisg.scs.edpo.factory.application.ports.in.PublishNotificationCommand;
import ch.unisg.scs.edpo.factory.application.ports.out.EventPublisherPort;
import ch.unisg.scs.edpo.factory.domain.ErrorEventDto;
import ch.unisg.scs.edpo.factory.domain.InfoEventDto;
import ch.unisg.scs.edpo.factory.domain.ManufacturingCompleteEventDto;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.validation.constraints.NotNull;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.UUID;

@RequiredArgsConstructor
@Slf4j
@Service
public class EventPublishingService implements EventPublishingUseCase {

    private final EventPublisherPort eventPublisherPort;
    private final ObjectMapper objectMapper;

    @Value("${kafka.topics.error:error.v1}")
    private String errorTopic;

    @Value("${kafka.topics.info:info.v1}")
    private String infoTopic;

    @Value("${kafka.topics.order-complete:order.complete.v1}")
    private String orderCompleteTopic;

    @Override
    public void publishError(PublishNotificationCommand command) throws RuntimeException {
        var correlationId = command.correlationId();
        var orderId = command.orderId();
        var payload = new ErrorEventDto(command.message(), orderId.toString(), correlationId.toString());
        try {
            eventPublisherPort.publish(errorTopic, null, objectMapper.writeValueAsString(payload));
        } catch (JsonProcessingException e) {
            log.error("Could not serialize ErrorTopicDto to JSON: {}", e.getMessage());
            throw new RuntimeException(e);
        }
    }

    @Override
    public void publishInfo(PublishNotificationCommand command) throws RuntimeException {
        var correlationId = command.correlationId();
        var orderId = command.orderId();
        var payload = new InfoEventDto(command.message(), orderId.toString(), correlationId.toString());
        try {
            eventPublisherPort.publish(infoTopic, null, objectMapper.writeValueAsString(payload));
        } catch (JsonProcessingException e) {
            log.error("Could not serialize InfoTopicDto to JSON: {}", e.getMessage());
            throw new RuntimeException(e);
        }
    }

    @Override
    public void publishOrderComplete(@NotNull UUID orderId, @NotNull UUID correlationId){
        log.debug("Order complete message");
        var payload = new ManufacturingCompleteEventDto(orderId.toString(), correlationId.toString());
        try {
            eventPublisherPort.publish(orderCompleteTopic, null, objectMapper.writeValueAsString(payload));
        } catch (JsonProcessingException e) {
            log.error("Could not serialize ManufacturingCompleteEventDto to JSON: {}", e.getMessage());
            throw new RuntimeException(e);
        }
    }
}
