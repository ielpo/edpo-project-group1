package ch.unisg.scs.edpo.dashboard;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class ConfigController {

    @Value("${inventory.service.url:http://localhost:8001}")
    private String inventoryServiceUrl;

    @GetMapping("/config.json")
    public Map<String, String> getConfig() {
        return Map.of("inventoryUrl", inventoryServiceUrl);
    }

}
