package ch.unisg.scs.edpo.order.adapters.out;

import ch.unisg.scs.edpo.order.application.ports.out.ReserveInventoryPort;
import ch.unisg.scs.edpo.order.application.ports.out.ReserveInventoryResult;
import ch.unisg.scs.edpo.order.domain.ReserveInventoryDto;
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
    public ReserveInventoryResult reserve(String url, ReserveInventoryDto request) {
        String normalizedBaseUrl = url.endsWith("/") ? url.substring(0, url.length() - 1) : url;

        // TODO: Remove this fallback after a stable inventory service base URL is always provided.
        // Temporary behavior: keep flow runnable when default placeholder URL is used.
        if (isPlaceholderUrl(normalizedBaseUrl)) {
            ResponseEntity<String> placeholderResponse = restClient.get()
                    .uri(normalizedBaseUrl)
                    .retrieve()
                    .toEntity(String.class);

            int placeholderStatusCode = placeholderResponse.getStatusCode().value();
            String placeholderBody = placeholderResponse.getBody() == null ? "" : placeholderResponse.getBody();
            return new ReserveInventoryResult(placeholderStatusCode, placeholderBody);
        }

        String reserveUrl = normalizedBaseUrl + "/reserve/" + request.orderId();

        ResponseEntity<String> response = restClient.post()
                .uri(reserveUrl)
                .body(request)
                .retrieve()
                .toEntity(String.class);

        int statusCode = response.getStatusCode().value();
        String body = response.getBody() == null ? "" : response.getBody();
        return new ReserveInventoryResult(statusCode, body);
    }

    private boolean isPlaceholderUrl(String baseUrl) {
        return baseUrl.contains("httpbin.org/get");
    }
}