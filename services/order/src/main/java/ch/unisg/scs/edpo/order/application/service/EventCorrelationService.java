package ch.unisg.scs.edpo.order.application.service;

import ch.unisg.scs.edpo.order.application.port.in.CorrelateEventCommand;
import ch.unisg.scs.edpo.order.application.port.in.EventCorrelationUseCase;
import ch.unisg.scs.edpo.order.application.port.out.MessageCorrelationPort;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class EventCorrelationService implements EventCorrelationUseCase {

    private final MessageCorrelationPort messageCorrelationPort;

    public EventCorrelationService(MessageCorrelationPort messageCorrelationPort) {
        this.messageCorrelationPort = messageCorrelationPort;
    }

    @Override
    public boolean correlateOrderComplete(CorrelateEventCommand command) {
        if (!hasKeys(command)) {
            return false;
        }
        return messageCorrelationPort.correlate(
                "order.complete.v1",
                command.orderId(),
                command.correlationId(),
                Map.of(
                        "factoryCompletionOrderId", command.orderId(),
                        "factoryCompletionCorrelationId", command.correlationId()
                )
        );
    }

    @Override
    public boolean correlateError(CorrelateEventCommand command) {
        if (!hasKeys(command)) {
            return false;
        }
        return messageCorrelationPort.correlate(
            "error.v1",
                command.orderId(),
                command.correlationId(),
                Map.of(
                        "factoryErrorOrderId", command.orderId(),
                        "factoryErrorCorrelationId", command.correlationId()
                )
        );
    }

    private boolean hasKeys(CorrelateEventCommand command) {
        return command.orderId() != null
                && !command.orderId().isBlank()
                && command.correlationId() != null
                && !command.correlationId().isBlank();
    }
}
