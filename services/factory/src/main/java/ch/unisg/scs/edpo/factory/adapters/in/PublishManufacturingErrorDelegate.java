package ch.unisg.scs.edpo.factory.adapters.in;

import ch.unisg.scs.edpo.factory.application.ports.in.EventPublishingUseCase;
import ch.unisg.scs.edpo.factory.application.ports.in.PublishNotificationCommand;
import ch.unisg.scs.edpo.factory.domain.OrderDto;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

import java.util.UUID;

@Slf4j
@RequiredArgsConstructor
@Component("publishManufacturingErrorDelegate")
public class PublishManufacturingErrorDelegate implements JavaDelegate {

    private final EventPublishingUseCase eventPublishingUseCase;
    private final ObjectMapper objectMapper;

    @Override
    public void execute(DelegateExecution execution) {
        try {
            var order = objectMapper.readValue(execution.getVariable("order").toString(), OrderDto.class);
            var correlationId = UUID.fromString(execution.getVariable("correlationId").toString());

            // TODO: update such that Dashboard service can show status
            eventPublishingUseCase.publishError(new PublishNotificationCommand(
                    order.orderId(),
                    correlationId,
                    "Manufacturing failed"
            ));
        } catch (Exception e) {
            log.error("Could not publish error message: {}", e.getMessage());
            execution.setVariable("errorPublishError", e.getMessage());
        }
    }
}
