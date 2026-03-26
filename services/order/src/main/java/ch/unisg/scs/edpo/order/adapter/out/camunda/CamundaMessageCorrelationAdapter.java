package ch.unisg.scs.edpo.order.adapter.out.camunda;

import ch.unisg.scs.edpo.order.application.port.out.MessageCorrelationPort;
import org.operaton.bpm.engine.MismatchingMessageCorrelationException;
import org.operaton.bpm.engine.RuntimeService;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
public class CamundaMessageCorrelationAdapter implements MessageCorrelationPort {

    private final RuntimeService runtimeService;

    public CamundaMessageCorrelationAdapter(RuntimeService runtimeService) {
        this.runtimeService = runtimeService;
    }

    @Override
    public boolean correlate(String messageName, String orderId, String correlationId, Map<String, Object> variables) {
        try {
            runtimeService.createMessageCorrelation(messageName)
                    .processInstanceVariableEquals("orderId", orderId)
                    .processInstanceVariableEquals("correlationId", correlationId)
                    .setVariables(variables)
                    .correlate();
            return true;
        } catch (MismatchingMessageCorrelationException e) {
            return false;
        }
    }
}