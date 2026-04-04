package ch.unisg.scs.edpo.factory.application.ports.in;

import ch.unisg.scs.edpo.factory.domain.FetchInventoryDto;
import ch.unisg.scs.edpo.factory.domain.OrderDto;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.util.UUID;

public interface RequestItemsFromInventoryPort {
    FetchInventoryDto request(@NotNull OrderDto order);
}
