package ch.unisg.scs.edpo.factory.config;

import jakarta.validation.constraints.NotBlank;

public record RobotFlows(@NotBlank String toHoldingPosition, @NotBlank String toInventory, @NotBlank String toColorSensor, @NotBlank String toDistanceSensor, @NotBlank String toBuildArea) {
}
