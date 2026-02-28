package ch.unisg.scs;

import com.google.common.io.Resources;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;

import java.io.IOException;
import java.io.InputStream;
import java.time.Duration;
import java.util.List;
import java.util.Properties;

@Slf4j
public class Consumer {
    public static void main(String[] args) throws IOException {
        try (InputStream props = Resources.getResource("consumer.properties").openStream()) {
            Properties properties = new Properties();
            properties.load(props);

            try (KafkaConsumer<String, Object> consumer = new KafkaConsumer<>(properties)) {
                consumer.subscribe(List.of("events"));

                //noinspection InfiniteLoopStatement
                while (true) {
                    ConsumerRecords<String, Object> records = consumer.poll(Duration.ofMillis(8));
                    for (ConsumerRecord<String, Object> record : records) {
                        switch (record.topic()) {
                            case "events":
                                log.info("Received {} - key: {}, value: {}, partition: {}", record.topic(), record.key(), record.value(), record.partition());
                                break;
                            default:
                                throw new IllegalStateException("Not subscribed to topic: " + record.topic());
                        }
                    }
                }
            }
        }
    }
}
