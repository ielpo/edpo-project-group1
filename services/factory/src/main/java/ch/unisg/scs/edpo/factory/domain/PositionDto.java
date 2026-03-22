package ch.unisg.scs.edpo.factory.domain;

import lombok.NonNull;

public record PositionDto(@NonNull Integer x, @NonNull Integer y, @NonNull BlockColour color) {
}
