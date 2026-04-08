package ch.unisg.scs.edpo.factory.adapters.out;

import ch.unisg.scs.edpo.factory.adapters.out.dtos.RelativeMovementCommandDto;
import ch.unisg.scs.edpo.factory.adapters.out.dtos.SuctionCupCommandDto;
import ch.unisg.scs.edpo.factory.application.ports.out.MoveBlockPort;
import ch.unisg.scs.edpo.factory.domain.AssemblyPositionDto;
import ch.unisg.scs.edpo.factory.domain.InventoryPositionDto;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
@Slf4j
public class ControlRobotAdapter implements MoveBlockPort {
    private final RestClient restClient;
    private final Environment environment;

    public ControlRobotAdapter(RestClient.Builder restClientBuilder, Environment environment) {
        this.environment = environment;
        this.restClient = restClientBuilder
                .baseUrl(environment.getRequiredProperty("edpo.robot.right.url"))
                .build();
    }

    private void toHoldingPosition(){
        var response = restClient.post().uri("/run-flow?filename=" + environment.getRequiredProperty("edpo.robot.flows.to-holding-position")).retrieve().toBodilessEntity().getStatusCode();
        if(response.value() != 200){
            log.error("Could not move to holding position, HTTP response {}", response.value());
            throw new RuntimeException("Could not move to holding position");
        }
    }

    @Override
    public void initialize(){
        var status = restClient.put().uri("/home").retrieve().toBodilessEntity().getStatusCode();
        if(status.value() != 200){
            log.error("Could not home robot, HTTP response {}", status.value());
            throw new RuntimeException("Could not home robot");
        }
    }

    @Override
    public void fromInventory(InventoryPositionDto position) {
        var xOffset = Float.parseFloat(environment.getRequiredProperty("edpo.robot.inventory.x-step")) * position.x();
        var yOffset = Float.parseFloat(environment.getRequiredProperty("edpo.robot.inventory.y-step")) * position.y();
        var zPickup = Float.parseFloat(environment.getRequiredProperty("edpo.robot.inventory.z-pickup"));

        var response = restClient.post()
                .uri("/run-flow?filename=" + environment.getRequiredProperty("edpo.robot.flows.to-inventory"))
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if(response.value() != 200){
            log.error("Could not move to inventory, HTTP response {}", response.value());
            throw new RuntimeException("Could not move to inventory");
        }
        log.info("Moving to inventory");

        response = restClient.post()
                .uri("/move-relative")
                .body(new RelativeMovementCommandDto(xOffset, yOffset))
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if(response.value() != 200){
            log.error("Could not move  to block position, HTTP response {}", response.value());
            throw new RuntimeException("Could not move to block position");
        }
        log.info("Moving to selected block");

        response = restClient.put()
                .uri("/suction-cup")
                .body(new SuctionCupCommandDto(true))
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if(response.value() != 200){
            log.error("Could not activate suction cup, HTTP response {}", response.value());
            throw new RuntimeException("Could not activate suction cup");
        }

        response = restClient.post()
                .uri("/move-relative")
                .body(new RelativeMovementCommandDto(zPickup))
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if(response.value() != 200){
            log.error("Could not move pickup position, HTTP response {}", response.value());
            throw new RuntimeException("Could not move to pickup position");
        }

        response = restClient.post()
                .uri("/move-relative")
                .body(new RelativeMovementCommandDto(-4 * zPickup))
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if(response.value() != 200){
            log.error("Could not pick up block, HTTP response {}", response.value());
            throw new RuntimeException("Could not pick up block");
        }
        log.info("Picked up block, moving to holding position");

        toHoldingPosition();
    }

    @Override
    public void toColor() {
        var response = restClient.post()
                .uri("/run-flow?filename=" + environment.getRequiredProperty("edpo.robot.flows.to-color-sensor"))
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if(response.value() != 200){
            log.error("Could not move to color sensor, HTTP response {}", response.value());
            throw new RuntimeException("Could not move to color sensor");
        }
    }

    @Override
    public void toDistanceSensor() {
        var response = restClient.post()
                .uri("/run-flow?filename=" + environment.getRequiredProperty("edpo.robot.flows.to-distance-sensor"))
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if(response.value() != 200){
            log.error("Could not move to distance sensor, HTTP response {}", response.value());
            throw new RuntimeException("Could not move to distance sensor");
        }
    }

    @Override
    public void toDiscard() {

    }

    @Override
    public void toAssembly(AssemblyPositionDto position) {
        // TODO: implement logic to place blocks using relative movements
        var response = restClient.post().uri("/run-flow?filename=" + environment.getRequiredProperty("edpo.robot.flows.to-assembly")).retrieve().toBodilessEntity().getStatusCode();
        if(response.value() != 200){
            log.error("Could not move to assembly position, HTTP response {}", response.value());
            throw new RuntimeException("Could not move to assembly position");
        }
    }
}
