package ch.unisg.scs.edpo.factory.adapters.out;

import ch.unisg.scs.edpo.factory.application.ports.out.ReadColorPort;
import ch.unisg.scs.edpo.factory.domain.BlockColor;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.springframework.core.env.Environment;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import tools.jackson.databind.ObjectMapper;

import java.time.Duration;
import java.util.Map;
import java.util.Properties;

@Slf4j
@Component
public class ColorSensorAdapter implements ReadColorPort {

    private static final String COLOR_RAW_TOPIC = "sensor.color.raw.v1";
    private static final int READINGS = 10;
    private static final int INTERVAL_MS = 200;
    private static final int TIMEOUT_MS = 6000;

    private final RestClient restClient;
    private final String bootstrapServers;
    private final ObjectMapper objectMapper;

    public ColorSensorAdapter(RestClient.Builder restClientBuilder, Environment environment, ObjectMapper objectMapper) {
        this.restClient = restClientBuilder
                .baseUrl(environment.getRequiredProperty("edpo.sensor.color.url"))
                .build();
        this.bootstrapServers = environment.getRequiredProperty("spring.kafka.bootstrap-servers");
        this.objectMapper = objectMapper;
    }

    @Override
    public BlockColor get(String cubeId) {
        try (var consumer = createConsumer(cubeId)) {
            // Assign all partitions and seek to end so we only read new messages
            var partitions = consumer.partitionsFor(COLOR_RAW_TOPIC).stream()
                    .map(p -> new TopicPartition(p.topic(), p.partition()))
                    .toList();
            consumer.assign(partitions);
            consumer.seekToEnd(partitions);
            consumer.poll(Duration.ofMillis(100)); // apply lazy seek

            // Tell the sensor to start publishing readings for this cube
            restClient.post().uri("/activate")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of("cubeId", cubeId, "readings", READINGS, "intervalMs", INTERVAL_MS))
                    .retrieve().toBodilessEntity();

            // Wait for the first reading matching our cubeId
            var deadline = System.currentTimeMillis() + TIMEOUT_MS;
            while (System.currentTimeMillis() < deadline) {
                for (var record : consumer.poll(Duration.ofMillis(500))) {
                    if (cubeId.equals(record.key())) {
                        return classify(record.value());
                    }
                }
            }
        } catch (Exception e) {
            log.error("Error reading colour for cube {}", cubeId, e);
        }
        log.error("Timeout waiting for colour reading, cubeId={}", cubeId);
        return BlockColor.UNKNOWN;
    }

    private KafkaConsumer<String, String> createConsumer(String cubeId) {
        var props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, "factory-color-" + cubeId);
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "latest");
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "false");
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        return new KafkaConsumer<>(props);
    }

    private BlockColor classify(String json) {
        try {
            var node = objectMapper.readTree(json);
            int r = node.get("r").intValue();
            int g = node.get("g").intValue();
            int b = node.get("b").intValue();
            if (r > g && g > b) return BlockColor.YELLOW;
            if (r > g && r > b) return BlockColor.RED;
            if (g > r && g > b) return BlockColor.GREEN;
            if (b > r && b > g) return BlockColor.BLUE;
        } catch (Exception e) {
            log.error("Failed to parse colour event: {}", json, e);
        }
        return BlockColor.UNKNOWN;
    }
}
