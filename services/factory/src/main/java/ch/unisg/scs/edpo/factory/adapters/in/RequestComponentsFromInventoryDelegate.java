package ch.unisg.scs.edpo.factory.adapters.in;

import ch.unisg.scs.edpo.factory.application.ports.in.RequestItemsFromInventoryPort;
import ch.unisg.scs.edpo.factory.domain.ItemType;
import ch.unisg.scs.edpo.factory.domain.OrderDto;
import lombok.RequiredArgsConstructor;
import org.operaton.bpm.engine.delegate.BpmnError;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.operaton.bpm.engine.runtime.Job;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.UUID;

@Component("requestComponentsFromInventoryDelegate")
@RequiredArgsConstructor
public class RequestComponentsFromInventoryDelegate implements JavaDelegate {
    private static final String ERROR_CODE = "INVENTORY_FETCH_FAILED";

    private final RequestItemsFromInventoryPort requestItemsFromInventory;
    
    @Override
    public void execute(DelegateExecution delegateExecution) {
        try {
            var order = readOrder(delegateExecution.getVariable("order"));
            var fetchInventory = requestItemsFromInventory.request(order);
            var inventoryVariable = fetchInventory.positions().stream()
                .map(position -> Map.of(
                    "x", position.x(),
                    "y", position.y(),
                    "color", position.color().name()
                ))
                .toList();
            delegateExecution.setVariable("inventory", inventoryVariable);
        } catch (RuntimeException ex) {
            if (isFinalRetryAttempt(delegateExecution)) {
                throw new BpmnError(ERROR_CODE, "Failed to fetch inventory: " + ex.getMessage());
            }
            throw ex;
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

            return currentJob != null && currentJob.getRetries() <= 1;
        } catch (Exception ignored) {
            return false;
        }
    }

    private OrderDto readOrder(Object orderVariable) {
        if (orderVariable instanceof OrderDto orderDto) {
            return orderDto;
        }
        if (orderVariable instanceof Map<?, ?> map) {
            Object orderIdRaw = map.get("orderId");
            Object itemTypeRaw = map.get("itemType");
            if (orderIdRaw == null || itemTypeRaw == null) {
                throw new IllegalArgumentException("Missing order fields in process variable 'order'");
            }
            return new OrderDto(
                    UUID.fromString(orderIdRaw.toString()),
                    ItemType.valueOf(itemTypeRaw.toString())
            );
        }
        throw new IllegalArgumentException("Unsupported process variable type for 'order': " + orderVariable);
    }
}
