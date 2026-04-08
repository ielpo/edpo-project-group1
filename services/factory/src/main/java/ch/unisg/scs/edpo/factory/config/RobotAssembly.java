package ch.unisg.scs.edpo.factory.config;

import jakarta.validation.constraints.NotNull;

public record RobotAssembly(@NotNull Float cubeSize, @NotNull Float zInitial) {
}
