package ch.unisg.scs.edpo.order.application.port.out;

import ch.unisg.scs.edpo.order.domain.ReserveInventoryDto;

public interface ReserveInventoryPort {
    ReserveInventoryResult reserve(String url, ReserveInventoryDto request);
}
