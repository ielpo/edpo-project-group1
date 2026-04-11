package ch.unisg.scs.edpo.order.adapters.in.camunda;

import ch.unisg.scs.edpo.order.application.port.in.EventPublishingUseCase;
import ch.unisg.scs.edpo.order.application.port.in.PublishNotificationCommand;
import ch.unisg.scs.edpo.order.application.port.in.PublishResult;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

@Component("publishInventoryReservationInfoDelegate")
public class PublishInventoryReservationInfoDelegate implements JavaDelegate {

    private final EventPublishingUseCase eventPublishingUseCase;

    public PublishInventoryReservationInfoDelegate(EventPublishingUseCase eventPublishingUseCase) {
        this.eventPublishingUseCase = eventPublishingUseCase;
    }

    @Override
    public void execute(DelegateExecution execution) {
        PublishResult result = eventPublishingUseCase.publishInfo(new PublishNotificationCommand(
                asString(execution.getVariable("orderId")),
                asString(execution.getVariable("correlationId")),
                buildMessage(execution)
        ));

        execution.setVariable("correlationId", result.correlationId());
        if (!result.success()) {
            execution.setVariable("infoPublishError", result.errorMessage());
        }
    }

    private String buildMessage(DelegateExecution execution) {
        Object value = execution.getVariable("inventoryReservationErrorMessage");
        if (value != null && !value.toString().isBlank()) {
            return "Reservation not possible: " + value;
        }
        return "Reservation not possible due to insufficient inventory.";
    }

    private String asString(Object value) {
        return value == null ? null : value.toString();
    }
}
