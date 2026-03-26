package ch.unisg.scs.edpo.order.delegates;

import ch.unisg.scs.edpo.order.application.ports.out.RestoreInventoryResult;
import ch.unisg.scs.edpo.order.application.services.RestoreInventoryUseCase;
import org.operaton.bpm.engine.delegate.BpmnError;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

@Component("restockInventoryDelegate")
public class RestockInventoryDelegate implements JavaDelegate {

    private static final String DEFAULT_URL = "http://localhost:8000";
    private static final String ERROR_CODE = "INVENTORY_RESTORE_FAILED";

    private final RestoreInventoryUseCase restoreInventoryUseCase;

    public RestockInventoryDelegate(RestoreInventoryUseCase restoreInventoryUseCase) {
        this.restoreInventoryUseCase = restoreInventoryUseCase;
    }

    @Override
    public void execute(DelegateExecution execution) {
        Object configuredUrl = execution.getVariable("inventoryServiceUrl");
        String url = configuredUrl == null ? DEFAULT_URL : configuredUrl.toString();

        Object orderIdVar = execution.getVariable("orderId");
        if (orderIdVar == null || orderIdVar.toString().isBlank()) {
            throw new BpmnError(ERROR_CODE, "Missing orderId — cannot restore inventory");
        }
        String orderId = orderIdVar.toString();

        try {
            RestoreInventoryResult result = restoreInventoryUseCase.execute(url, orderId);

            if (result.statusCode() < 200 || result.statusCode() >= 300) {
                throw new BpmnError(ERROR_CODE,
                        "Inventory restore failed with status " + result.statusCode() + ": " + result.body());
            }

            execution.setVariable("inventoryRestoreStatus", result.statusCode());
        } catch (BpmnError e) {
            throw e;
        } catch (Exception e) {
            throw new BpmnError(ERROR_CODE, "Failed to restore inventory: " + e.getMessage());
        }
    }
}
