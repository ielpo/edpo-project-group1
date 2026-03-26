package ch.unisg.scs.edpo.order.adapter.in.camunda;

import ch.unisg.scs.edpo.order.application.port.in.EventPublishingUseCase;
import ch.unisg.scs.edpo.order.application.port.in.PublishNotificationCommand;
import ch.unisg.scs.edpo.order.application.port.in.PublishResult;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

@Component("publishFactoryErrorDelegate")
public class PublishFactoryErrorDelegate implements JavaDelegate {

    private final EventPublishingUseCase eventPublishingUseCase;

    public PublishFactoryErrorDelegate(EventPublishingUseCase eventPublishingUseCase) {
        this.eventPublishingUseCase = eventPublishingUseCase;
    }

    @Override
    public void execute(DelegateExecution execution) {
        PublishResult result = eventPublishingUseCase.publishError(new PublishNotificationCommand(
                asString(execution.getVariable("orderId")),
                asString(execution.getVariable("correlationId")),
                "Factory reported an error"
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
