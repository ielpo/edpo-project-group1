package ch.unisg.scs.edpo.order.adapter.in.camunda;

import ch.unisg.scs.edpo.order.application.port.in.EventPublishingUseCase;
import ch.unisg.scs.edpo.order.application.port.in.PublishManufactureCommand;
import ch.unisg.scs.edpo.order.application.port.in.PublishResult;
import org.operaton.bpm.engine.delegate.BpmnError;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

@Component("publishManufactureOrderDelegate")
public class PublishManufactureOrderDelegate implements JavaDelegate {

    private static final String ERROR_CODE = "MANUFACTURE_COMMAND_PUBLISH_FAILED";
    private final EventPublishingUseCase eventPublishingUseCase;

    public PublishManufactureOrderDelegate(EventPublishingUseCase eventPublishingUseCase) {
        this.eventPublishingUseCase = eventPublishingUseCase;
    }

    @Override
    public void execute(DelegateExecution execution) {
        String orderId = required(execution.getVariable("orderId"), "Missing orderId. Expected it to be set during inventory reservation.");
        String itemType = readItemType(execution);
        String correlationId = asString(execution.getVariable("correlationId"));

        PublishResult result = eventPublishingUseCase.publishManufactureCommand(
                new PublishManufactureCommand(orderId, itemType, correlationId)
        );

        if (!result.success()) {
            throw new BpmnError(ERROR_CODE, "Failed to publish manufacture command: " + result.errorMessage());
        }

        execution.setVariable("correlationId", result.correlationId());
        execution.setVariable("manufactureCommandTopic", "order.manufacture.v1");
    }

    private String readItemType(DelegateExecution execution) {
        Object selectedItemType = execution.getVariable("selectedItemType");
        if (selectedItemType != null && !selectedItemType.toString().isBlank()) {
            return selectedItemType.toString();
        }
        return required(execution.getVariable("select_item"), "Invalid item type for manufacture command");
    }

    private String required(Object value, String message) {
        if (value == null || value.toString().isBlank()) {
            throw new BpmnError(ERROR_CODE, message);
        }
        return value.toString();
    }

    private String asString(Object value) {
        return value == null ? null : value.toString();
    }
}
