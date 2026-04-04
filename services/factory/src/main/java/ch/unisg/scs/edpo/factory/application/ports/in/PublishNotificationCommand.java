package ch.unisg.scs.edpo.factory.application.ports.in;

public record PublishNotificationCommand(String orderId, String correlationId, String message) {
}
