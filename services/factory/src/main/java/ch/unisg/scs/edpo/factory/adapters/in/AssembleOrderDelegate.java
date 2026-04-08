package ch.unisg.scs.edpo.factory.adapters.in;

import ch.unisg.scs.edpo.factory.application.ports.in.AssembleOrderPort;
import ch.unisg.scs.edpo.factory.domain.InventoryPositionDto;
import ch.unisg.scs.edpo.factory.domain.OrderDto;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

import java.util.List;

@Slf4j
@Component("assembleOrderDelegate")
@RequiredArgsConstructor
public class AssembleOrderDelegate implements JavaDelegate {
    private final AssembleOrderPort assembleOrder;
    private final ObjectMapper objectMapper;

    @Override
    public void execute(DelegateExecution delegateExecution) {
        try {
            List<InventoryPositionDto> inventory = objectMapper.readValue(
                    delegateExecution.getVariable("inventory").toString(),
                    objectMapper.getTypeFactory().constructCollectionType(List.class, InventoryPositionDto.class));
            var order = objectMapper.readValue(delegateExecution.getVariable("order").toString(), OrderDto.class);
            assembleOrder.assemble(inventory, order);
        } catch (JsonProcessingException e) {
            log.error("Could not deserialize variables: {}", e.getMessage());
            throw new RuntimeException();
        }
    }
}
