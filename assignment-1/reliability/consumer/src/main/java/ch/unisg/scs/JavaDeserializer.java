package ch.unisg.scs;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.common.errors.SerializationException;
import org.apache.kafka.common.serialization.Deserializer;

import java.nio.charset.StandardCharsets;
import java.util.Map;

// Note: deserialized objects are stored by default as LinkedHashMap by ObjectMapper jackson

@Slf4j
public class JavaDeserializer implements Deserializer<Object> {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public void configure(Map<String, ?> configs, boolean isKey) {
    }

    @Override
    public Object deserialize(String topic, byte[] data) {
        try {
            if (data == null) {
                log.error("Null received at deserializing");
                return null;
            }
            return objectMapper.readValue(new String(data, StandardCharsets.UTF_8), Object.class);
        } catch (Exception e) {
            throw new SerializationException("Error when deserializing byte[] to object");
        }
    }

    @Override
    public void close() {
    }

}
