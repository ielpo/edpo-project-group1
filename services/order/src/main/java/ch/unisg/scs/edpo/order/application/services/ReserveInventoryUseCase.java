package ch.unisg.scs.edpo.order.application.services;

import ch.unisg.scs.edpo.order.application.ports.out.ReserveInventoryPort;
import ch.unisg.scs.edpo.order.application.ports.out.ReserveInventoryResult;
import ch.unisg.scs.edpo.order.domain.ReserveInventoryDto;
import org.springframework.stereotype.Service;

@Service
public class ReserveInventoryUseCase {

    private final ReserveInventoryPort reserveInventoryPort;

    public ReserveInventoryUseCase(ReserveInventoryPort reserveInventoryPort) {
        this.reserveInventoryPort = reserveInventoryPort;
    }

    public ReserveInventoryResult execute(String url, ReserveInventoryDto request) {
        return reserveInventoryPort.reserve(url, request);
    }
}