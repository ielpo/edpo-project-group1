package ch.unisg.scs.edpo.factory.adapters.out;

import ch.unisg.scs.edpo.factory.application.ports.out.MoveBlockPort;
import ch.unisg.scs.edpo.factory.domain.AssemblyPositionDto;
import ch.unisg.scs.edpo.factory.domain.InventoryPositionDto;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.env.Environment;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
@Slf4j
public class ControlRobotAdapter implements MoveBlockPort {
    private final RestClient restClient;

    public ControlRobotAdapter(RestClient.Builder restClientBuilder, Environment environment) {
        this.restClient = restClientBuilder
                .baseUrl(environment.getRequiredProperty("edpo.robot.right.url"))
                .build();
    }

    @PostConstruct
    public void initialize(){
        var status = restClient.put().uri("/home").retrieve().toBodilessEntity().getStatusCode();
        if(status.value() != 200){
            log.error("Could not home robot, HTTP response {}", status.value());
            throw new RuntimeException("Could not home robot");
        }
    }

    @Override
    public void fromInventory(InventoryPositionDto position) {

    }

    @Override
    public void toColor() {

    }

    @Override
    public void toDistanceSensor() {

    }

    @Override
    public void toDiscard() {

    }

    @Override
    public void toAssembly(AssemblyPositionDto position) {

    }
}
