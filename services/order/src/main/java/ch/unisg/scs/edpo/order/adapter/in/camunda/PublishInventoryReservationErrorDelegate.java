package ch.unisg.scs.edpo.order.adapter.in.camunda;

import ch.unisg.scs.edpo.order.application.port.in.EventPublishingUseCase;
import ch.unisg.scs.edpo.order.application.port.in.PublishNotificationCommand;
import ch.unisg.scs.edpo.order.application.port.in.PublishResult;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

@Component("publishInventoryReservationErrorDelegate")
public class PublishInventoryReservationErrorDelegate implements JavaDelegate {

    private final EventPublishingUseCase eventPublishingUseCase;

    public PublishInventoryReservationErrorDelegate(EventPublishingUseCase eventPublishingUseCase) {
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
        Object value = execution.getVariable("inventoryReservationErrorMessage");
        if (value != null && !value.toString().isBlank()) {
            return "Inventory service unavailable: " + value;
        }
        return "Inventory service unavailable during reservation.";
    }

    private String asString(Object value) {
        return value == null ? null : value.toString();
    }
}
