package ch.unisg.scs.edpo.order.application.port.in;

public interface EventPublishingUseCase {
    PublishResult publishManufactureCommand(PublishManufactureCommand command);

    PublishResult publishInfo(PublishNotificationCommand command);

    PublishResult publishError(PublishNotificationCommand command);
}
