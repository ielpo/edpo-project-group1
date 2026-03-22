package ch.unisg.scs.edpo.factory.adapters.in;

import ch.unisg.scs.edpo.factory.application.ports.in.AssembleOrderPort;
import ch.unisg.scs.edpo.factory.domain.FetchInventoryDto;
import ch.unisg.scs.edpo.factory.domain.OrderDto;
import lombok.RequiredArgsConstructor;
import org.operaton.bpm.engine.delegate.DelegateExecution;
import org.operaton.bpm.engine.delegate.JavaDelegate;

@RequiredArgsConstructor
public class AssembleOrderDelegate implements JavaDelegate {
    private final AssembleOrderPort assembleOrder;
    
    @Override
    public void execute(DelegateExecution delegateExecution) {
        var inventory = (FetchInventoryDto) delegateExecution.getVariable("inventory");
        var order = (OrderDto) delegateExecution.getVariable("order");
        assembleOrder.assemble(inventory.positions(), order);
    }
}
