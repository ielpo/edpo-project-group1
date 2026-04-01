package ch.unisg.scs.edpo.order.adapter.out.persistence;

import ch.unisg.scs.edpo.order.application.port.out.RestoreInventoryPort;
import ch.unisg.scs.edpo.order.application.port.out.RestoreInventoryResult;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

@Component
public class RestClientRestoreInventoryAdapter implements RestoreInventoryPort {

    private final HttpClient httpClient = HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1)
            .build();

    @Override
    public RestoreInventoryResult restore(String url, String orderId) {
        String normalizedBaseUrl = url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
        String restoreUrl = normalizedBaseUrl + "/restore";
        String json = String.format("{\"orderId\":\"%s\"}", orderId);

        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(restoreUrl))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(json))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            String body = response.body() == null ? "" : response.body();
            return new RestoreInventoryResult(response.statusCode(), body);
        } catch (Exception e) {
            throw new RuntimeException("Failed to call inventory restore: " + e.getMessage(), e);
        }
    }
}
