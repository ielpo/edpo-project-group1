package ch.unisg.scs.edpo.factory.adapters.in;

import ch.unisg.scs.edpo.factory.domain.OrderManufactureDto;
import lombok.RequiredArgsConstructor;
import org.operaton.bpm.engine.RuntimeService;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import tools.jackson.databind.ObjectMapper;

import java.util.Map;

@RequiredArgsConstructor
@Component
public class ManufactureOrderCommandKafkaListener {
    private final RuntimeService runtime;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @KafkaListener(topics = "order.manufacture.v1")
    void listener(String payloadJson) {
        OrderManufactureDto payload;
        try {
            payload = objectMapper.readValue(payloadJson, OrderManufactureDto.class);
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid order.manufacture.v1 payload", e);
        }

        runtime.createMessageCorrelation("orderMessage")
            .setVariable("order", Map.of(
                "orderId", payload.order().orderId().toString(),
                "itemType", payload.order().itemType().name()
            ))
            .setVariable("correlationId", payload.correlationId().toString())
                .correlateStartMessage();
    }
}
