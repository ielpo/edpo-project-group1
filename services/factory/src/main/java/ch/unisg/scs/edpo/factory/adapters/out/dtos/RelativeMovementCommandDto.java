package ch.unisg.scs.edpo.factory.adapters.out.dtos;

import jakarta.annotation.Nullable;
import jakarta.validation.constraints.NotNull;

public record RelativeMovementCommandDto(@Nullable Float x, @Nullable Float y, @Nullable Float z, @Nullable Float r) {
    public RelativeMovementCommandDto(@NotNull Float x, @NotNull Float y) {
        this(x, y, null, null);
    }
    public RelativeMovementCommandDto(@NotNull Float z) {
        this(null, null, z, null);
    }
}
