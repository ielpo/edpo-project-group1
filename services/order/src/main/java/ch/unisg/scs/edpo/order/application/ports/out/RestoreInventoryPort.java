package ch.unisg.scs.edpo.order.application.ports.out;

public interface RestoreInventoryPort {
    RestoreInventoryResult restore(String url, String orderId);
}
