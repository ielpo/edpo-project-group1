package ch.unisg.scs.edpo.factory.application.ports.in;

import ch.unisg.scs.edpo.factory.domain.PositionDto;
import jakarta.validation.constraints.NotNull;

import java.util.List;

public interface AssembleOrderPort {
    void assemble(@NotNull List<PositionDto> positions);
}
