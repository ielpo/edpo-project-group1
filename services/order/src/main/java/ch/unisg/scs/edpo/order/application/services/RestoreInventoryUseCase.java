package ch.unisg.scs.edpo.order.application.services;

import ch.unisg.scs.edpo.order.application.ports.out.RestoreInventoryPort;
import ch.unisg.scs.edpo.order.application.ports.out.RestoreInventoryResult;
import org.springframework.stereotype.Service;

@Service
public class RestoreInventoryUseCase {

    private final RestoreInventoryPort restoreInventoryPort;

    public RestoreInventoryUseCase(RestoreInventoryPort restoreInventoryPort) {
        this.restoreInventoryPort = restoreInventoryPort;
    }

    public RestoreInventoryResult execute(String url, String orderId) {
        return restoreInventoryPort.restore(url, orderId);
    }
}
