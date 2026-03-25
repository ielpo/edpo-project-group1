package ch.unisg.scs.edpo.order.delegates;

import ch.unisg.scs.edpo.order.application.ports.out.ReserveInventoryResult;
import ch.unisg.scs.edpo.order.application.services.ReserveInventoryUseCase;
import ch.unisg.scs.edpo.order.domain.BlockColor;
import ch.unisg.scs.edpo.order.domain.ItemType;
import ch.unisg.scs.edpo.order.domain.ReserveInventoryDto;
import org.operaton.bpm.engine.delegate.BpmnError;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

import java.util.UUID;

@Component("reserveInventoryDelegate")
public class ReserveInventoryDelegate implements JavaDelegate {

    // TODO: Replace placeholder default with inventory service base URL (for example: http://localhost:8000).
    private static final String DEFAULT_URL = "http://localhost:8000";
    private static final String ERROR_CODE = "INVENTORY_SERVICE_UNAVAILABLE";

    private final ReserveInventoryUseCase reserveInventoryUseCase;

    public ReserveInventoryDelegate(ReserveInventoryUseCase reserveInventoryUseCase) {
        this.reserveInventoryUseCase = reserveInventoryUseCase;
    }

    @Override
    public void execute(DelegateExecution execution) {
        Object configuredUrl = execution.getVariable("inventoryServiceUrl");
        String url = configuredUrl == null ? DEFAULT_URL : configuredUrl.toString();
        String orderId = getOrCreateOrderId(execution);
        ItemType selectedItemType = getRequiredEnum(execution, "select_item", ItemType.class);
        BlockColor selectedColor = getRequiredEnum(execution, "select_color", BlockColor.class);
        int requiredBlockCount = getRequiredBlockCount(selectedItemType);
        ReserveInventoryDto reserveInventoryDto = new ReserveInventoryDto(orderId, requiredBlockCount, selectedColor);

        execution.setVariable("orderId", orderId);
        execution.setVariable("selectedItemType", selectedItemType.name());
        execution.setVariable("selectedColor", selectedColor.name());
        execution.setVariable("requiredBlockCount", requiredBlockCount);

        try {
            ReserveInventoryResult result = reserveInventoryUseCase.execute(url, reserveInventoryDto);
            boolean success = result.statusCode() >= 200 && result.statusCode() < 300;

            execution.setVariable("inventoryReservationStatus", result.statusCode());
            execution.setVariable("inventoryReservationResponse", result.body());
            execution.setVariable("inventoryReservationSuccess", success);

            if (!success) {
                String errorMessage = "Inventory service returned status " + result.statusCode();
                execution.setVariable("inventoryReservationErrorMessage", errorMessage);
                if (result.statusCode() == 409) {
                    execution.setVariable("inventoryReservationFailureType", "INSUFFICIENT_BLOCKS");
                    return;
                }
                execution.setVariable("inventoryReservationFailureType", "TECHNICAL_OR_INVALID_REQUEST");
                throw new BpmnError(ERROR_CODE, errorMessage);
            }

            execution.setVariable("inventoryReservationFailureType", null);
        } catch (BpmnError e) {
            throw e;
        } catch (Exception e) {
            execution.setVariable("inventoryReservationSuccess", false);
            execution.setVariable("inventoryReservationFailureType", "TECHNICAL_OR_INVALID_REQUEST");
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
            case CHAIR -> 1;
            case TABLE, SHELF -> 2;
            case CLOSET -> 3;
        };
    }

    private String getOrCreateOrderId(DelegateExecution execution) {
        Object existingOrderId = execution.getVariable("orderId");
        if (existingOrderId != null && !existingOrderId.toString().isBlank()) {
            return existingOrderId.toString();
        }

        String businessKey = execution.getProcessBusinessKey();
        if (businessKey != null && !businessKey.isBlank()) {
            return businessKey;
        }

        return UUID.randomUUID().toString();
    }
}