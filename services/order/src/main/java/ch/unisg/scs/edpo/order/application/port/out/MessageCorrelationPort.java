package ch.unisg.scs.edpo.order.application.port.out;

import java.util.Map;

public interface MessageCorrelationPort {
    boolean correlate(String messageName, String orderId, String correlationId, Map<String, Object> variables);
}
