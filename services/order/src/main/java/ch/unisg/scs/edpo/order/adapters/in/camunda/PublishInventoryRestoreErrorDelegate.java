package ch.unisg.scs.edpo.order.adapters.in.camunda;

import ch.unisg.scs.edpo.order.application.port.in.EventPublishingUseCase;
import ch.unisg.scs.edpo.order.application.port.in.PublishNotificationCommand;
import ch.unisg.scs.edpo.order.application.port.in.PublishResult;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

@Component("publishInventoryRestoreErrorDelegate")
public class PublishInventoryRestoreErrorDelegate implements JavaDelegate {

    private final EventPublishingUseCase eventPublishingUseCase;

    public PublishInventoryRestoreErrorDelegate(EventPublishingUseCase eventPublishingUseCase) {
        this.eventPublishingUseCase = eventPublishingUseCase;
    }

    @Override
    public void execute(DelegateExecution execution) {
        PublishResult result = eventPublishingUseCase.publishError(new PublishNotificationCommand(
                asString(execution.getVariable("orderId")),
                asString(execution.getVariable("correlationId")),
                buildMessage(execution)
        ));

        execution.setVariable("correlationId", result.correlationId());
        if (!result.success()) {
            execution.setVariable("errorPublishError", result.errorMessage());
        }
    }

    private String buildMessage(DelegateExecution execution) {
        String stage = asString(execution.getVariable("inventoryRestoreFailureStage"));
        String details = asString(execution.getVariable("inventoryRestoreErrorMessage"));

        String base = switch (stage) {
            case "AFTER_TIMEOUT" -> "Inventory restore failed after manufacturing timeout";
            case "AFTER_FACTORY_ERROR" -> "Inventory restore failed after factory error";
            default -> "Inventory restore failed";
        };

        if (details != null && !details.isBlank()) {
            return base + ": " + details;
        }
        return base + ".";
    }

    private String asString(Object value) {
        return value == null ? null : value.toString();
    }
}