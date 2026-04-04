package ch.unisg.scs.edpo.factory.application.ports.in;

public record PublishResult(String correlationId, String errorMessage) {
    public boolean success() {
        return errorMessage == null || errorMessage.isBlank();
    }
}
