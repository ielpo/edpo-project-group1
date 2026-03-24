package ch.unisg.scs.edpo.order.adapters.out;

import ch.unisg.scs.edpo.order.application.ports.out.ReserveInventoryPort;
import ch.unisg.scs.edpo.order.application.ports.out.ReserveInventoryResult;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class RestClientReserveInventoryAdapter implements ReserveInventoryPort {

    private final RestClient restClient;

    public RestClientReserveInventoryAdapter(RestClient.Builder restClientBuilder) {
        this.restClient = restClientBuilder.build();
    }

    @Override
    public ReserveInventoryResult reserve(String url) {
        ResponseEntity<String> response = restClient.get()
                .uri(url)
                .retrieve()
                .toEntity(String.class);

        int statusCode = response.getStatusCode().value();
        String body = response.getBody() == null ? "" : response.getBody();
        return new ReserveInventoryResult(statusCode, body);
    }
}