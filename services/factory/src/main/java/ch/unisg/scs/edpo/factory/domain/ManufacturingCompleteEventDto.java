package ch.unisg.scs.edpo.factory.domain;

import jakarta.validation.constraints.NotBlank;

public record ManufacturingCompleteEventDto(@NotBlank String orderId, @NotBlank String correlationId) {
}
