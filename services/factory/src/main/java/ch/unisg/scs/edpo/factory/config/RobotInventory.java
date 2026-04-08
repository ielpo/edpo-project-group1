package ch.unisg.scs.edpo.factory.config;

import jakarta.validation.constraints.Negative;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record RobotInventory(@NotNull @Positive Float xStep, @NotNull @Positive Float yStep, @NotNull @Negative Float zPickup) {
}
