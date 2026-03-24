package ch.unisg.scs.edpo.order.application.ports.out;

public interface ReserveInventoryPort {
    ReserveInventoryResult reserve(String url);
}