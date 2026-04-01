package ch.unisg.scs.edpo.order.adapter.in.camunda;

import ch.unisg.scs.edpo.order.application.port.in.EventPublishingUseCase;
import ch.unisg.scs.edpo.order.application.port.in.PublishNotificationCommand;
import ch.unisg.scs.edpo.order.application.port.in.PublishResult;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

@Component("publishFactoryInfoDelegate")
public class PublishFactoryInfoDelegate implements JavaDelegate {

    private final EventPublishingUseCase eventPublishingUseCase;

    public PublishFactoryInfoDelegate(EventPublishingUseCase eventPublishingUseCase) {
        this.eventPublishingUseCase = eventPublishingUseCase;
    }

    @Override
    public void execute(DelegateExecution execution) {
        PublishResult result = eventPublishingUseCase.publishInfo(new PublishNotificationCommand(
                asString(execution.getVariable("orderId")),
                asString(execution.getVariable("correlationId")),
                "Manufacturing succeeded via factory info feedback"
        ));

        execution.setVariable("correlationId", result.correlationId());
        if (!result.success()) {
            execution.setVariable("infoPublishError", result.errorMessage());
        }
    }

    private String asString(Object value) {
        return value == null ? null : value.toString();
    }
}
