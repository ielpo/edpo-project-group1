package ch.unisg.scs.edpo.order.adapter.in.camunda;

import ch.unisg.scs.edpo.order.application.port.in.InventoryWorkflowUseCase;
import ch.unisg.scs.edpo.order.application.port.in.ReserveInventoryCommand;
import ch.unisg.scs.edpo.order.application.port.in.ReserveInventoryOutcome;
import org.operaton.bpm.engine.delegate.BpmnError;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

@Component("reserveInventoryDelegate")
public class ReserveInventoryDelegate implements JavaDelegate {

    private static final String ERROR_CODE = "INVENTORY_SERVICE_UNAVAILABLE";
    private final InventoryWorkflowUseCase inventoryWorkflowUseCase;

    public ReserveInventoryDelegate(InventoryWorkflowUseCase inventoryWorkflowUseCase) {
        this.inventoryWorkflowUseCase = inventoryWorkflowUseCase;
    }

    @Override
    public void execute(DelegateExecution execution) {
        ReserveInventoryCommand command = new ReserveInventoryCommand(
                asString(execution.getVariable("inventoryServiceUrl")),
                asString(execution.getVariable("orderId")),
                execution.getProcessBusinessKey(),
                readItem(execution),
                readColor(execution)
        );

        ReserveInventoryOutcome outcome = inventoryWorkflowUseCase.reserveInventory(command);

        execution.setVariable("orderId", outcome.orderId());
        execution.setVariable("selectedItemType", outcome.selectedItemType());
        execution.setVariable("selectedColor", outcome.selectedColor());
        execution.setVariable("requiredBlockCount", outcome.requiredBlockCount());
        execution.setVariable("inventoryReservationStatus", outcome.statusCode());
        execution.setVariable("inventoryReservationResponse", outcome.responseBody());
        execution.setVariable("inventoryReservationSuccess", outcome.success());
        execution.setVariable("inventoryReservationFailureType", outcome.failureType());
        execution.setVariable("inventoryReservationErrorMessage", outcome.errorMessage());

        if (!outcome.success() && outcome.technicalFailure()) {
            throw new BpmnError(ERROR_CODE, "Inventory service not available: " + outcome.errorMessage());
        }
    }

    private String readItem(DelegateExecution execution) {
        Object selectedItem = execution.getVariable("selectedItemType");
        if (selectedItem != null && !selectedItem.toString().isBlank()) {
            return selectedItem.toString();
        }
        return asString(execution.getVariable("select_item"));
    }

    private String readColor(DelegateExecution execution) {
        Object selectedColor = execution.getVariable("selectedColor");
        if (selectedColor != null && !selectedColor.toString().isBlank()) {
            return selectedColor.toString();
        }
        return asString(execution.getVariable("select_color"));
    }

    private String asString(Object value) {
        return value == null ? null : value.toString();
    }
}
