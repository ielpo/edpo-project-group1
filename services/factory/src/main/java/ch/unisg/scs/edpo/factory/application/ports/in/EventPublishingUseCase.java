package ch.unisg.scs.edpo.factory.application.ports.in;

public interface EventPublishingUseCase {
    PublishResult publishError(PublishNotificationCommand command);
}
