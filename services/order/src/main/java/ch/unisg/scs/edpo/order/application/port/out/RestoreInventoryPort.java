package ch.unisg.scs.edpo.order.application.port.out;

public interface RestoreInventoryPort {
    RestoreInventoryResult restore(String url, String orderId);
}
