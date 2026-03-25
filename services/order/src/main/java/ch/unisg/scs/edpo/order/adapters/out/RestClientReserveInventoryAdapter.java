package ch.unisg.scs.edpo.order.adapters.out;

import ch.unisg.scs.edpo.order.application.ports.out.ReserveInventoryPort;
import ch.unisg.scs.edpo.order.application.ports.out.ReserveInventoryResult;
import ch.unisg.scs.edpo.order.domain.ReserveInventoryDto;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

@Component
public class RestClientReserveInventoryAdapter implements ReserveInventoryPort {

    private final HttpClient httpClient = HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1)
            .build();

    @Override
    public ReserveInventoryResult reserve(String url, ReserveInventoryDto request) {
        String normalizedBaseUrl = url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
        String reserveUrl = normalizedBaseUrl + "/reserve/" + request.orderId();
        String json = String.format("{\"count\":%d,\"color\":\"%s\"}", request.count(), request.color().name());

        try {
            HttpRequest httpRequest = HttpRequest.newBuilder()
                    .uri(URI.create(reserveUrl))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(json))
                    .build();

            HttpResponse<String> response = httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofString());
            String body = response.body() == null ? "" : response.body();
            return new ReserveInventoryResult(response.statusCode(), body);
        } catch (Exception e) {
            throw new RuntimeException("Failed to call inventory service: " + e.getMessage(), e);
        }
    }
}