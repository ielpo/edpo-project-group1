package ch.unisg.scs.edpo.kafkastreams.web;

import ch.unisg.scs.edpo.kafkastreams.domain.BlockColorEvent;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.KeyValue;
import org.apache.kafka.streams.StoreQueryParameters;
import org.apache.kafka.streams.state.KeyValueIterator;
import org.apache.kafka.streams.state.QueryableStoreTypes;
import org.apache.kafka.streams.state.ReadOnlyKeyValueStore;
import org.springframework.http.ResponseEntity;
import org.springframework.kafka.config.StreamsBuilderFactoryBean;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/inventory")
public class InventoryQueryController {

    private final StreamsBuilderFactoryBean factoryBean;

    public InventoryQueryController(StreamsBuilderFactoryBean factoryBean) {
        this.factoryBean = factoryBean;
    }

    // Returns all blocks currently in the inventory KTable (keyed by cubeId).
    @GetMapping
    public ResponseEntity<Map<String, BlockColorEvent>> getInventory() {
        ReadOnlyKeyValueStore<String, BlockColorEvent> store = store("inventory-store",
                QueryableStoreTypes.keyValueStore());

        Map<String, BlockColorEvent> result = new HashMap<>();
        try (KeyValueIterator<String, BlockColorEvent> it = store.all()) {
            while (it.hasNext()) {
                KeyValue<String, BlockColorEvent> kv = it.next();
                result.put(kv.key, kv.value);
            }
        }
        return ResponseEntity.ok(result);
    }

    // Returns the entry for a specific cubeId.
    @GetMapping("/{cubeId}")
    public ResponseEntity<BlockColorEvent> getBlock(@PathVariable String cubeId) {
        ReadOnlyKeyValueStore<String, BlockColorEvent> store = store("inventory-store",
                QueryableStoreTypes.keyValueStore());
        BlockColorEvent entry = store.get(cubeId);
        return entry != null ? ResponseEntity.ok(entry) : ResponseEntity.notFound().build();
    }

    private <T> T store(String name, org.apache.kafka.streams.state.QueryableStoreType<T> type) {
        KafkaStreams streams = factoryBean.getKafkaStreams();
        if (streams == null) throw new IllegalStateException("Kafka Streams not running");
        return streams.store(StoreQueryParameters.fromNameAndType(name, type));
    }
}
