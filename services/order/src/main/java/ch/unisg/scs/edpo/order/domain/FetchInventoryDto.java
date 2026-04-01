package ch.unisg.scs.edpo.order.domain;

import lombok.NonNull;

import java.util.List;

public record FetchInventoryDto(
        @NonNull List<InventoryPositionDto> positions
) {
}