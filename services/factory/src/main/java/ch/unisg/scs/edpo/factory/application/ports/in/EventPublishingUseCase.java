package ch.unisg.scs.edpo.factory.application.ports.in;

import java.util.UUID;

public interface EventPublishingUseCase {
    void publishError(PublishNotificationCommand command);
    void publishInfo(PublishNotificationCommand command);
    void publishOrderComplete(UUID orderId, UUID correlationId);
}
