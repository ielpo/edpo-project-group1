package ch.unisg.scs.edpo.order.adapters.in.camunda;

import ch.unisg.scs.edpo.order.application.port.in.InventoryWorkflowUseCase;
import ch.unisg.scs.edpo.order.application.port.in.RestoreInventoryCommand;
import ch.unisg.scs.edpo.order.application.port.in.RestoreInventoryOutcome;
import org.operaton.bpm.engine.delegate.BpmnError;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.operaton.bpm.engine.runtime.Job;
import org.springframework.stereotype.Component;

@Component("restockInventoryDelegate")
public class RestockInventoryDelegate implements JavaDelegate {

    private static final String ERROR_CODE_TIMEOUT_PATH = "INVENTORY_RESTORE_TIMEOUT_FAILED";
    private static final String ERROR_CODE_FACTORY_PATH = "INVENTORY_RESTORE_FACTORY_FAILED";
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
            String message = "Failed to restore inventory: " + outcome.errorMessage();
            execution.setVariable("inventoryRestoreFailureStage", determineRestoreFailureStage(execution));
            execution.setVariable("inventoryRestoreErrorMessage", outcome.errorMessage());

            if (isFinalRetryAttempt(execution)) {
                throw new BpmnError(resolveErrorCode(execution), message);
            }
            throw new RuntimeException(message);
        }

        execution.setVariable("inventoryRestoreStatus", outcome.statusCode());
    }

    private boolean isFinalRetryAttempt(DelegateExecution execution) {
        try {
            Job currentJob = execution.getProcessEngineServices()
                    .getManagementService()
                    .createJobQuery()
                    .processInstanceId(execution.getProcessInstanceId())
                    .activityId(execution.getCurrentActivityId())
                    .singleResult();

            return currentJob != null && currentJob.getRetries() <= 1;
        } catch (Exception ignored) {
            return false;
        }
    }

    private String asString(Object value) {
        return value == null ? null : value.toString();
    }

    private String resolveErrorCode(DelegateExecution execution) {
        return switch (execution.getCurrentActivityId()) {
            case "Activity_0uhz0y6" -> ERROR_CODE_TIMEOUT_PATH;
            case "Activity_0ezfqp2" -> ERROR_CODE_FACTORY_PATH;
            default -> ERROR_CODE_TIMEOUT_PATH;
        };
    }

    private String determineRestoreFailureStage(DelegateExecution execution) {
        return switch (execution.getCurrentActivityId()) {
            case "Activity_0uhz0y6" -> "AFTER_TIMEOUT";
            case "Activity_0ezfqp2" -> "AFTER_FACTORY_ERROR";
            default -> "UNKNOWN";
        };
    }
}
