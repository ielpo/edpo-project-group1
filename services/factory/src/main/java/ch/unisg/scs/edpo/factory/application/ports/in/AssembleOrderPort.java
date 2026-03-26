package ch.unisg.scs.edpo.factory.application.ports.in;

import ch.unisg.scs.edpo.factory.domain.OrderDto;
import ch.unisg.scs.edpo.factory.domain.InventoryPositionDto;
import jakarta.validation.constraints.NotNull;

import java.util.List;

public interface AssembleOrderPort {
    void assemble(@NotNull List<InventoryPositionDto> positions, @NotNull OrderDto order);
}
