package ch.unisg.scs.edpo.factory.domain;

import lombok.NonNull;

import java.util.UUID;

public record OrderDto(@NonNull UUID orderId, @NonNull ItemType itemType) {
}
