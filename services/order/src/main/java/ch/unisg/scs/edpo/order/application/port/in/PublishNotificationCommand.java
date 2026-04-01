package ch.unisg.scs.edpo.order.application.port.in;

public record PublishNotificationCommand(String orderId, String correlationId, String message) {
}
