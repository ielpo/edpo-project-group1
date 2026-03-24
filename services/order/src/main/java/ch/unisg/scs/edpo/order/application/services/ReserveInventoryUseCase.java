package ch.unisg.scs.edpo.order.application.services;

import ch.unisg.scs.edpo.order.application.ports.out.ReserveInventoryPort;
import ch.unisg.scs.edpo.order.application.ports.out.ReserveInventoryResult;
import org.springframework.stereotype.Service;

@Service
public class ReserveInventoryUseCase {

    private final ReserveInventoryPort reserveInventoryPort;

    public ReserveInventoryUseCase(ReserveInventoryPort reserveInventoryPort) {
        this.reserveInventoryPort = reserveInventoryPort;
    }

    public ReserveInventoryResult execute(String url) {
        return reserveInventoryPort.reserve(url);
    }
}