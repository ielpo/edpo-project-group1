package ch.unisg.scs.edpo.order.application.port.in;

public record PublishManufactureCommand(String orderId, String itemType, String correlationId) {
}
