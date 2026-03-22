package ch.unisg.scs.edpo.factory.domain;

import jakarta.validation.constraints.NotNull;

public record InventoryPositionDto(@NotNull Integer x, @NotNull Integer y, @NotNull BlockColour colour) {
}
