package ch.unisg.scs.edpo.order.application.port.in;

public record ReserveInventoryCommand(
        String inventoryServiceUrl,
        String existingOrderId,
        String processBusinessKey,
        String selectedItem,
        String selectedColor
) {
}
