package ch.unisg.scs.edpo.factory.adapters.in;

import ch.unisg.scs.edpo.factory.application.ports.in.AssembleOrderPort;
import ch.unisg.scs.edpo.factory.domain.BlockColor;
import ch.unisg.scs.edpo.factory.domain.FetchInventoryDto;
import ch.unisg.scs.edpo.factory.domain.InventoryPositionDto;
import ch.unisg.scs.edpo.factory.domain.ItemType;
import ch.unisg.scs.edpo.factory.domain.OrderDto;
import lombok.RequiredArgsConstructor;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@Component("assembleOrderDelegate")
@RequiredArgsConstructor
public class AssembleOrderDelegate implements JavaDelegate {
    private final AssembleOrderPort assembleOrder;
    
    @Override
    public void execute(DelegateExecution delegateExecution) {
        var inventory = readInventory(delegateExecution.getVariable("inventory"));
        var order = readOrder(delegateExecution.getVariable("order"));
        assembleOrder.assemble(inventory, order);
    }

    private List<InventoryPositionDto> readInventory(Object inventoryVariable) {
        if (inventoryVariable instanceof FetchInventoryDto fetchInventoryDto) {
            return fetchInventoryDto.positions();
        }
        if (inventoryVariable instanceof List<?> list) {
            return list.stream()
                    .map(this::readInventoryPosition)
                    .toList();
        }
        throw new IllegalArgumentException("Unsupported process variable type for 'inventory': " + inventoryVariable);
    }

    private InventoryPositionDto readInventoryPosition(Object rawPosition) {
        if (!(rawPosition instanceof Map<?, ?> map)) {
            throw new IllegalArgumentException("Unsupported inventory entry type: " + rawPosition);
        }
        Object xRaw = map.get("x");
        Object yRaw = map.get("y");
        Object colorRaw = map.get("color");
        if (xRaw == null || yRaw == null || colorRaw == null) {
            throw new IllegalArgumentException("Missing inventory fields in process variable 'inventory'");
        }
        return new InventoryPositionDto(
                Integer.parseInt(xRaw.toString()),
                Integer.parseInt(yRaw.toString()),
                BlockColor.valueOf(colorRaw.toString())
        );
    }

    private OrderDto readOrder(Object orderVariable) {
        if (orderVariable instanceof OrderDto orderDto) {
            return orderDto;
        }
        if (orderVariable instanceof Map<?, ?> map) {
            Object orderIdRaw = map.get("orderId");
            Object itemTypeRaw = map.get("itemType");
            if (orderIdRaw == null || itemTypeRaw == null) {
                throw new IllegalArgumentException("Missing order fields in process variable 'order'");
            }
            return new OrderDto(
                    UUID.fromString(orderIdRaw.toString()),
                    ItemType.valueOf(itemTypeRaw.toString())
            );
        }
        throw new IllegalArgumentException("Unsupported process variable type for 'order': " + orderVariable);
    }
}
