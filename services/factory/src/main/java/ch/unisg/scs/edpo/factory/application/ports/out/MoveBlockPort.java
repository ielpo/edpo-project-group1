package ch.unisg.scs.edpo.factory.application.ports.out;

import ch.unisg.scs.edpo.factory.domain.AssemblyPositionDto;
import ch.unisg.scs.edpo.factory.domain.InventoryPositionDto;
import jakarta.validation.constraints.NotNull;

public interface MoveBlockPort {
    void fromInventory(@NotNull InventoryPositionDto position);
    void toColor();
    void toDistanceSensor();
    void toDiscard();
    void toAssembly(@NotNull AssemblyPositionDto position);
}
