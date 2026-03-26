package ch.unisg.scs.edpo.order.adapter.in.camunda;

import ch.unisg.scs.edpo.order.application.port.in.InventoryWorkflowUseCase;
import ch.unisg.scs.edpo.order.application.port.in.RestoreInventoryCommand;
import ch.unisg.scs.edpo.order.application.port.in.RestoreInventoryOutcome;
import org.operaton.bpm.engine.delegate.BpmnError;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

@Component("restockInventoryDelegate")
public class RestockInventoryDelegate implements JavaDelegate {

    private static final String ERROR_CODE = "INVENTORY_RESTORE_FAILED";
    private final InventoryWorkflowUseCase inventoryWorkflowUseCase;

    public RestockInventoryDelegate(InventoryWorkflowUseCase inventoryWorkflowUseCase) {
        this.inventoryWorkflowUseCase = inventoryWorkflowUseCase;
    }

    @Override
    public void execute(DelegateExecution execution) {
        RestoreInventoryOutcome outcome = inventoryWorkflowUseCase.restoreInventory(
                new RestoreInventoryCommand(
                        asString(execution.getVariable("inventoryServiceUrl")),
                        asString(execution.getVariable("orderId"))
                )
        );

        if (!outcome.success()) {
            throw new BpmnError(ERROR_CODE, "Failed to restore inventory: " + outcome.errorMessage());
        }

        execution.setVariable("inventoryRestoreStatus", outcome.statusCode());
    }

    private String asString(Object value) {
        return value == null ? null : value.toString();
    }
}
