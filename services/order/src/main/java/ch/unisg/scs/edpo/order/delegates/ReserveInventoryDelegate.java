package ch.unisg.scs.edpo.order.delegates;

import ch.unisg.scs.edpo.order.application.ports.out.ReserveInventoryResult;
import ch.unisg.scs.edpo.order.application.services.ReserveInventoryUseCase;
import ch.unisg.scs.edpo.order.domain.BlockColour;
import ch.unisg.scs.edpo.order.domain.ItemType;
import org.operaton.bpm.engine.delegate.BpmnError;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

@Component("reserveInventoryDelegate")
public class ReserveInventoryDelegate implements JavaDelegate {

    private static final String DEFAULT_URL = "https://httpbin.org/get";
    private static final String ERROR_CODE = "INVENTORY_SERVICE_UNAVAILABLE";

    private final ReserveInventoryUseCase reserveInventoryUseCase;

    public ReserveInventoryDelegate(ReserveInventoryUseCase reserveInventoryUseCase) {
        this.reserveInventoryUseCase = reserveInventoryUseCase;
    }

    @Override
    public void execute(DelegateExecution execution) {
        Object configuredUrl = execution.getVariable("inventoryServiceUrl");
        String url = configuredUrl == null ? DEFAULT_URL : configuredUrl.toString();
        ItemType selectedItemType = getRequiredEnum(execution, "select_item", ItemType.class);
        BlockColour selectedColour = getRequiredEnum(execution, "select_colour", BlockColour.class);
        int requiredBlockCount = getRequiredBlockCount(selectedItemType);

        try {
            ReserveInventoryResult result = reserveInventoryUseCase.execute(url);
            boolean success = result.statusCode() >= 200 && result.statusCode() < 300;

            execution.setVariable("selectedItemType", selectedItemType.name());
            execution.setVariable("selectedColour", selectedColour.name());
            execution.setVariable("requiredBlockCount", requiredBlockCount);
            execution.setVariable("inventoryReservationStatus", result.statusCode());
            execution.setVariable("inventoryReservationResponse", result.body());
            execution.setVariable("inventoryReservationSuccess", success);

            if (!success) {
                String errorMessage = "Inventory service returned status " + result.statusCode();
                execution.setVariable("inventoryReservationErrorMessage", errorMessage);
                throw new BpmnError(ERROR_CODE, errorMessage);
            }
        } catch (BpmnError e) {
            throw e;
        } catch (Exception e) {
            execution.setVariable("inventoryReservationSuccess", false);
            execution.setVariable("inventoryReservationErrorMessage", e.getMessage());
            throw new BpmnError(ERROR_CODE, "Inventory service not available: " + e.getMessage());
        }
    }

    private String getVariableAsString(DelegateExecution execution, String variableName) {
        Object value = execution.getVariable(variableName);
        return value == null ? "" : value.toString();
    }

    private <T extends Enum<T>> T getRequiredEnum(DelegateExecution execution, String variableName, Class<T> enumClass) {
        String value = getVariableAsString(execution, variableName);
        try {
            return Enum.valueOf(enumClass, value);
        } catch (IllegalArgumentException e) {
            throw new BpmnError(ERROR_CODE, "Invalid " + variableName + " value: " + value);
        }
    }

    private int getRequiredBlockCount(ItemType itemType) {
        return switch (itemType) {
            case Chair -> 1;
            case Table, Shelf -> 2;
            case Closet -> 3;
        };
    }
}