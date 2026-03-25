package ch.unisg.scs.edpo.order.domain;

import lombok.NonNull;

public record ReserveInventoryDto(
        @NonNull String orderId,
        int count,
        @NonNull BlockColor color
) {
}