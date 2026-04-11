package ch.unisg.scs.edpo.factory.domain;

import jakarta.validation.constraints.NotBlank;

public record InfoEventDto(@NotBlank String message, @NotBlank String orderId, @NotBlank String correlationId) {
}
