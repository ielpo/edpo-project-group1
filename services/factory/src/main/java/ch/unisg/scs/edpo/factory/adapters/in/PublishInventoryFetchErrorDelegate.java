package ch.unisg.scs.edpo.factory.adapters.in;

import ch.unisg.scs.edpo.factory.application.ports.in.EventPublishingUseCase;
import ch.unisg.scs.edpo.factory.application.ports.in.PublishNotificationCommand;
import ch.unisg.scs.edpo.factory.application.ports.in.PublishResult;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component("publishInventoryFetchErrorDelegate")
public class PublishInventoryFetchErrorDelegate implements JavaDelegate {

    private final EventPublishingUseCase eventPublishingUseCase;

    public PublishInventoryFetchErrorDelegate(EventPublishingUseCase eventPublishingUseCase) {
        this.eventPublishingUseCase = eventPublishingUseCase;
    }

    @Override
    public void execute(DelegateExecution execution) {
        String orderId = asString(execution.getVariable("orderId"));
        if (orderId == null) {
            Object order = execution.getVariable("order");
            if (order instanceof Map<?, ?> orderMap) {
                Object rawOrderId = orderMap.get("orderId");
                if (rawOrderId != null) {
                    orderId = rawOrderId.toString();
                }
            }
        }

        PublishResult result = eventPublishingUseCase.publishError(new PublishNotificationCommand(
                orderId,
                asString(execution.getVariable("correlationId")),
                buildMessage(execution)
        ));

        execution.setVariable("correlationId", result.correlationId());
        if (!result.success()) {
            execution.setVariable("errorPublishError", result.errorMessage());
        }
    }

    private String buildMessage(DelegateExecution execution) {
        Object detail = execution.getVariable("inventoryFetchErrorMessage");
        if (detail != null && !detail.toString().isBlank()) {
            return "Inventory fetch failed: " + detail;
        }
        return "Inventory fetch failed in factory workflow.";
    }

    private String asString(Object value) {
        if (value == null) {
            return null;
        }
        String text = value.toString();
        return text.isBlank() ? null : text;
    }
}
