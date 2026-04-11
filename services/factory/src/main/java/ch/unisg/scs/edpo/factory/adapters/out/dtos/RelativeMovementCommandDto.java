package ch.unisg.scs.edpo.factory.adapters.out.dtos;

import com.fasterxml.jackson.annotation.JsonInclude;
import jakarta.annotation.Nullable;
import jakarta.validation.constraints.NotNull;
import tools.jackson.databind.annotation.JsonSerialize;

public record RelativeMovementCommandDto(@NotNull Float x, @NotNull Float y, @NotNull Float z, @NotNull Float r) {
    public RelativeMovementCommandDto(@NotNull Float x, @NotNull Float y) {
        this(x, y, 0f, 0f);
    }
    public RelativeMovementCommandDto(@NotNull Float z) {
        this(0f, 0f, z, 0f);
    }
}
