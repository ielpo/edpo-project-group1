package ch.unisg.scs.edpo.factory.application.ports.out;

import ch.unisg.scs.edpo.factory.domain.AssemblyPositionDto;
import ch.unisg.scs.edpo.factory.domain.PositionDto;
import jakarta.validation.constraints.NotNull;

public interface MoveBlockPort {
    void fromInventory(@NotNull PositionDto position);
    void toColour();
    void toAssembly(@NotNull AssemblyPositionDto position);
}
