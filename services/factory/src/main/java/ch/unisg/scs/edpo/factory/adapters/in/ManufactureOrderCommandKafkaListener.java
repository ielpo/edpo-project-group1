package ch.unisg.scs.edpo.factory.adapters.in;

import ch.unisg.scs.edpo.factory.domain.OrderManufactureDto;
import lombok.RequiredArgsConstructor;
import org.operaton.bpm.engine.RuntimeService;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@RequiredArgsConstructor
@Component
public class ManufactureOrderCommandKafkaListener {
    private final RuntimeService runtime;

    @KafkaListener(topics = "order.manufacture.v1")
    void listener(OrderManufactureDto payload) {
        runtime.createMessageCorrelation("orderMessage")
                .setVariable("order", payload.order())
                .setVariable("correlationId", payload.correlationId())
                .correlateStartMessage();
    }
}
