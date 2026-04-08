package ch.unisg.scs.edpo.factory.application.ports.in;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.util.UUID;

public record PublishNotificationCommand(@NotNull UUID orderId, @NotNull UUID correlationId, @NotBlank String message) {
}
