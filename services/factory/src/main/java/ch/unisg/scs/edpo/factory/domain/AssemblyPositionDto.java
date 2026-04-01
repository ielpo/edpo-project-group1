package ch.unisg.scs.edpo.factory.domain;

import jakarta.validation.constraints.NotNull;

public record AssemblyPositionDto(@NotNull Integer x, @NotNull Integer y, @NotNull Integer z) {
}
