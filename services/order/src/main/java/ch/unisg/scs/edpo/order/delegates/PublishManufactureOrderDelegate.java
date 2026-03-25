package ch.unisg.scs.edpo.order.delegates;

import ch.unisg.scs.edpo.order.domain.ItemType;
import ch.unisg.scs.edpo.order.domain.OrderDto;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.operaton.bpm.engine.delegate.BpmnError;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.UUID;

@Component("publishManufactureOrderDelegate")
public class PublishManufactureOrderDelegate implements JavaDelegate {

    private static final String ERROR_CODE = "MANUFACTURE_COMMAND_PUBLISH_FAILED";

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;
    private final String manufactureTopic;

    public PublishManufactureOrderDelegate(
            KafkaTemplate<String, String> kafkaTemplate,
            ObjectMapper objectMapper,
            @Value("${kafka.topics.order-manufacture:order.manufacture.v1}") String manufactureTopic) {
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
        this.manufactureTopic = manufactureTopic;
    }

    @Override
    public void execute(DelegateExecution execution) {
        String orderId = getRequiredOrderId(execution);
        ItemType itemType = getRequiredItemType(execution);
        String correlationId = UUID.randomUUID().toString();

        OrderDto orderDto = new OrderDto(orderId, itemType);
        Map<String, Object> payload = Map.of(
                "order", orderDto,
                "correlationId", correlationId
        );

        try {
            String message = objectMapper.writeValueAsString(payload);
            kafkaTemplate.send(manufactureTopic, orderId, message);

            execution.setVariable("orderId", orderId);
            execution.setVariable("correlationId", correlationId);
            execution.setVariable("manufactureCommandTopic", manufactureTopic);
        } catch (JsonProcessingException e) {
            throw new BpmnError(ERROR_CODE, "Failed to serialize manufacture command: " + e.getMessage());
        } catch (Exception e) {
            throw new BpmnError(ERROR_CODE, "Failed to publish manufacture command: " + e.getMessage());
        }
    }

    private String getRequiredOrderId(DelegateExecution execution) {
        Object orderId = execution.getVariable("orderId");
        if (orderId != null && !orderId.toString().isBlank()) {
            return orderId.toString();
        }
        throw new BpmnError(ERROR_CODE, "Missing orderId. Expected it to be set during inventory reservation.");
    }

    private ItemType getRequiredItemType(DelegateExecution execution) {
        Object selectedItemType = execution.getVariable("selectedItemType");
        String rawValue = selectedItemType == null
                ? String.valueOf(execution.getVariable("select_item"))
                : selectedItemType.toString();

        try {
            return ItemType.valueOf(rawValue);
        } catch (Exception e) {
            throw new BpmnError(ERROR_CODE, "Invalid item type for manufacture command: " + rawValue);
        }
    }
}
