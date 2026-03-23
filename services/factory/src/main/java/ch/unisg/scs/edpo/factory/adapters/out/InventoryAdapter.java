package ch.unisg.scs.edpo.factory.adapters.out;

import ch.unisg.scs.edpo.factory.application.ports.out.FetchInventoryPort;
import ch.unisg.scs.edpo.factory.domain.FetchInventoryDto;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.UUID;

@Slf4j
@Component
public class InventoryAdapter implements FetchInventoryPort {
    private final RestClient restClient;

    public InventoryAdapter(RestClient.Builder restClientBuilder, Environment environment) {
        this.restClient = restClientBuilder
                .baseUrl(environment.getRequiredProperty("edpo.inventory.url"))
                .build();
    }

    @Override
    public FetchInventoryDto getInventoryPositions(UUID orderId) {
        return restClient.get().uri("/inventory?orderId={}", orderId).retrieve().body(FetchInventoryDto.class);
    }
}
