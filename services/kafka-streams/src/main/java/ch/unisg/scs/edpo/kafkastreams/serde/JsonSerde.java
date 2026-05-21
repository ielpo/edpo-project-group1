package ch.unisg.scs.edpo.kafkastreams.serde;

import org.apache.kafka.common.serialization.Deserializer;
import org.apache.kafka.common.serialization.Serde;
import org.apache.kafka.common.serialization.Serializer;
import tools.jackson.databind.ObjectMapper;

// Custom JSON serde using Jackson 3 (tools.jackson) directly.
// Replaces spring-kafka's JsonSerde which still internally references Jackson 2.
public class JsonSerde<T> implements Serde<T> {

    private final Class<T> type;
    private final ObjectMapper objectMapper;

    public JsonSerde(Class<T> type, ObjectMapper objectMapper) {
        this.type = type;
        this.objectMapper = objectMapper;
    }

    @Override
    public Serializer<T> serializer() {
        return (topic, data) -> data == null ? null : objectMapper.writeValueAsBytes(data);
    }

    @Override
    public Deserializer<T> deserializer() {
        return (topic, data) -> data == null ? null : objectMapper.readValue(data, type);
    }
}
