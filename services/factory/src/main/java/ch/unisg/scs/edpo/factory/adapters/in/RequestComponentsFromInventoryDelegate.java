package ch.unisg.scs.edpo.factory.adapters.in;

import ch.unisg.scs.edpo.factory.application.ports.in.RequestItemsFromInventoryPort;
import ch.unisg.scs.edpo.factory.domain.OrderDto;
import lombok.RequiredArgsConstructor;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;

@RequiredArgsConstructor
public class RequestComponentsFromInventoryDelegate implements JavaDelegate {
    private final RequestItemsFromInventoryPort requestItemsFromInventory;
    
    @Override
    public void execute(DelegateExecution delegateExecution) {
        var order = (OrderDto) delegateExecution.getVariable("order");
        var fetchInventory = requestItemsFromInventory.request(order);
        delegateExecution.setVariable("inventory", fetchInventory);
    }
}
