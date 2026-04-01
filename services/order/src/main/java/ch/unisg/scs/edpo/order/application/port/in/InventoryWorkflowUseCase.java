package ch.unisg.scs.edpo.order.application.port.in;

public interface InventoryWorkflowUseCase {
    ReserveInventoryOutcome reserveInventory(ReserveInventoryCommand command);

    RestoreInventoryOutcome restoreInventory(RestoreInventoryCommand command);
}
