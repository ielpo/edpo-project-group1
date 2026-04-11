package ch.unisg.scs.edpo.factory.adapters.in;

import ch.unisg.scs.edpo.factory.domain.OrderManufactureDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.operaton.bpm.engine.RuntimeService;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import tools.jackson.databind.ObjectMapper;

@Slf4j
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

        log.info("Received order with ID: {}", payload.order().orderId());

        runtime.createMessageCorrelation("orderMessage")
            .setVariable("order", objectMapper.writeValueAsString(payload.order()))
            .setVariable("correlationId", payload.correlationId().toString())
                .correlateStartMessage();
    }
}
