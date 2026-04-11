package ch.unisg.scs.edpo.order.adapters.in.camunda;

import ch.unisg.scs.edpo.order.application.port.in.EventPublishingUseCase;
import ch.unisg.scs.edpo.order.application.port.in.PublishNotificationCommand;
import ch.unisg.scs.edpo.order.application.port.in.PublishResult;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

@Component("publishManufacturingTimeoutErrorDelegate")
public class PublishManufacturingTimeoutErrorDelegate implements JavaDelegate {

    private final EventPublishingUseCase eventPublishingUseCase;

    public PublishManufacturingTimeoutErrorDelegate(EventPublishingUseCase eventPublishingUseCase) {
        this.eventPublishingUseCase = eventPublishingUseCase;
    }

    @Override
    public void execute(DelegateExecution execution) {
        PublishResult result = eventPublishingUseCase.publishError(new PublishNotificationCommand(
                asString(execution.getVariable("orderId")),
                asString(execution.getVariable("correlationId")),
                "Manufacturing timeout after 3 minutes"
        ));

        execution.setVariable("correlationId", result.correlationId());
        if (!result.success()) {
            execution.setVariable("errorPublishError", result.errorMessage());
        }
    }

    private String asString(Object value) {
        return value == null ? null : value.toString();
    }
}
