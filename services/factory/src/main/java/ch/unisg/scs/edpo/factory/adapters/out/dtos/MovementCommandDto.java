package ch.unisg.scs.edpo.factory.adapters.out.dtos;

import jakarta.annotation.Nullable;

public record MovementCommandDto(@Nullable Float x, @Nullable Float y, @Nullable Float z, @Nullable MovementMode mode) {
    public enum MovementMode {
        MOVE_LINEAR,
        MOVE_JOINT,
        JUMP,
    }
}
