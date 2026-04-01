package ch.unisg.scs.edpo.order.domain;

import lombok.NonNull;

public record OrderDto(@NonNull String orderId, @NonNull ItemType itemType) {
}
