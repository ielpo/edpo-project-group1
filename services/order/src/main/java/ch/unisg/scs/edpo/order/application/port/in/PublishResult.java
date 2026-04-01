package ch.unisg.scs.edpo.order.application.port.in;

public record PublishResult(String correlationId, String errorMessage) {
    public boolean success() {
        return errorMessage == null || errorMessage.isBlank();
    }
}
