package ch.unisg.scs.edpo.order.domain;

import lombok.NonNull;

import java.util.UUID;

public record OrderDto(@NonNull UUID orderId, @NonNull ItemType itemType) {
}
