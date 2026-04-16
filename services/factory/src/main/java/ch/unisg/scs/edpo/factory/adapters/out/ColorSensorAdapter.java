package ch.unisg.scs.edpo.factory.adapters.out;

import ch.unisg.scs.edpo.factory.application.ports.out.ReadColorPort;
import ch.unisg.scs.edpo.factory.domain.BlockColor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Slf4j
@Component
public class ColorSensorAdapter implements ReadColorPort {
    private final RestClient restClient;

    public ColorSensorAdapter(RestClient.Builder restClientBuilder, Environment environment) {
        restClient = restClientBuilder
                .baseUrl(environment.getRequiredProperty("edpo.sensor.color.url"))
                .build();
    }

    public BlockColor get() {
        var colors = restClient.get()
                .uri("/color")
                .retrieve()
                .body(RgbColor.class);
        if (colors == null) {
            log.error("No valid response from color sensor");
            return BlockColor.UNKNOWN;
        }
        log.debug("Got color: {}", colors);
        if (colors.r > colors.g && colors.g > colors.b) {
            return BlockColor.YELLOW;
        } else if (colors.r > colors.g && colors.r > colors.b) {
            return BlockColor.RED;
        } else if (colors.g > colors.r && colors.g > colors.b) {
            return BlockColor.GREEN;
        } else if (colors.b > colors.r && colors.b > colors.g) {
            return BlockColor.BLUE;
        } else {
            return BlockColor.UNKNOWN;
        }
    }

    private record RgbColor(int r, int g, int b) {
    }
}
