package ch.unisg.scs.edpo.order.adapters.in.camunda;

import ch.unisg.scs.edpo.order.application.port.in.InventoryWorkflowUseCase;
import ch.unisg.scs.edpo.order.application.port.in.ReserveInventoryCommand;
import ch.unisg.scs.edpo.order.application.port.in.ReserveInventoryOutcome;
import org.operaton.bpm.engine.delegate.BpmnError;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.operaton.bpm.engine.runtime.Job;
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
            if (isFinalRetryAttempt(execution)) {
                throw new BpmnError(ERROR_CODE, "Inventory service not available: " + outcome.errorMessage());
            }
            throw new RuntimeException("Inventory service not available: " + outcome.errorMessage());
        }
    }

    private boolean isFinalRetryAttempt(DelegateExecution execution) {
        try {
            Job currentJob = execution.getProcessEngineServices()
                    .getManagementService()
                    .createJobQuery()
                    .processInstanceId(execution.getProcessInstanceId())
                    .activityId(execution.getCurrentActivityId())
                    .singleResult();

            // If retries is 1, another technical failure would produce an incident.
            return currentJob != null && currentJob.getRetries() <= 1;
        } catch (Exception ignored) {
            // Fall back to technical retry path when job context cannot be resolved.
            return false;
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
