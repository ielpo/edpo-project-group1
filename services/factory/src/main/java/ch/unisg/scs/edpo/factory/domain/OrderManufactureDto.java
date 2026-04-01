package ch.unisg.scs.edpo.factory.domain;

import java.util.UUID;

public record OrderManufactureDto(OrderDto order, UUID correlationId){}
