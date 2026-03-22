package ch.unisg.scs.edpo.factory.application.ports.out;

import ch.unisg.scs.edpo.factory.domain.FetchInventoryDto;
import jakarta.validation.constraints.NotBlank;

import java.util.UUID;

public interface FetchInventoryPort {
    FetchInventoryDto getInventoryPositions(@NotBlank UUID orderId);
}
