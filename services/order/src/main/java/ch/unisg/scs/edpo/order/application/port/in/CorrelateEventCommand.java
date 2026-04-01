package ch.unisg.scs.edpo.order.application.port.in;

public record CorrelateEventCommand(String orderId, String correlationId) {
}
