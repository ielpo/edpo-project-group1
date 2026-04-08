package ch.unisg.scs.edpo.factory.adapters.in;

import ch.unisg.scs.edpo.factory.application.ports.in.RequestItemsFromInventoryPort;
import ch.unisg.scs.edpo.factory.domain.ItemType;
import ch.unisg.scs.edpo.factory.domain.OrderDto;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.operaton.bpm.engine.delegate.BpmnError;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.operaton.bpm.engine.runtime.Job;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.UUID;

@Slf4j
@Component("requestComponentsFromInventoryDelegate")
@RequiredArgsConstructor
public class RequestComponentsFromInventoryDelegate implements JavaDelegate {
    private static final String ERROR_CODE = "INVENTORY_FETCH_FAILED";

    private final RequestItemsFromInventoryPort requestItemsFromInventory;
    private final ObjectMapper objectMapper;
    
    @Override
    public void execute(DelegateExecution delegateExecution) {
        try {
            var order = objectMapper.readValue(delegateExecution.getVariable("order").toString(), OrderDto.class);
            var fetchInventory = requestItemsFromInventory.request(order);
            delegateExecution.setVariable("inventory", objectMapper.writeValueAsString(fetchInventory.positions()));
        } catch (Exception ex) {
            log.error("Could not fetch inventory: {}", ex.getMessage());
            if (isFinalRetryAttempt(delegateExecution)) {
                throw new BpmnError(ERROR_CODE, "Failed to fetch inventory: " + ex.getMessage());
            }
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
}
