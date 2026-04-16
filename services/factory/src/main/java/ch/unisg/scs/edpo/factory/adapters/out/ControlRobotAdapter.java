package ch.unisg.scs.edpo.factory.adapters.out;

import ch.unisg.scs.edpo.factory.adapters.out.dtos.RelativeMovementCommandDto;
import ch.unisg.scs.edpo.factory.adapters.out.dtos.SuctionCupCommandDto;
import ch.unisg.scs.edpo.factory.application.ports.out.MoveBlockPort;
import ch.unisg.scs.edpo.factory.config.RobotProperties;
import ch.unisg.scs.edpo.factory.domain.AssemblyPositionDto;
import ch.unisg.scs.edpo.factory.domain.InventoryPositionDto;
import lombok.extern.slf4j.Slf4j;
import org.operaton.bpm.engine.delegate.BpmnError;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.time.Duration;

@Component
@Slf4j
public class ControlRobotAdapter implements MoveBlockPort {
    private final RestClient restClient;
    private final RobotProperties config;

    public ControlRobotAdapter(RestClient.Builder restClientBuilder, RobotProperties robotProperties) {
        this.config = robotProperties;
        this.restClient = restClientBuilder
                .baseUrl(config.right().url())
                .build();
    }

    private void toHoldingPosition() {
        var response = restClient.post()
                .uri("/run-flow?filename=" + config.flows().toHoldingPosition())
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if (response.value() != 200) {
            log.error("Could not move to holding position, HTTP response {}", response.value());
            throw new BpmnError("Could not move to holding position");
        }
    }

    @Override
    public void initialize() {
        var status = restClient.put()
                .uri("/home")
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if (status.value() != 200) {
            log.error("Could not home robot, HTTP response {}", status.value());
            throw new BpmnError("Could not home robot");
        }
        wait(Duration.ofSeconds(20));
    }

    @Override
    public void fromInventory(InventoryPositionDto position) {
        var xOffset = config.inventory().xStep() * position.x();
        var yOffset = config.inventory().yStep() * position.y();
        var zPickup = config.inventory().zPickup();

        var response = restClient.post()
                .uri("/run-flow?filename=" + config.flows().toInventory())
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if (response.value() != 200) {
            log.error("Could not move to inventory, HTTP response {}", response.value());
            throw new BpmnError("Could not move to inventory");
        }
        log.info("Moving to inventory");

        response = restClient.post()
                .uri("/move-relative")
                .body(new RelativeMovementCommandDto(xOffset, yOffset))
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if (response.value() != 200) {
            log.error("Could not move  to block position, HTTP response {}", response.value());
            throw new BpmnError("Could not move to block position");
        }
        log.info("Moving to selected block");

        response = restClient.put()
                .uri("/suction-cup")
                .body(new SuctionCupCommandDto(true))
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if (response.value() != 200) {
            log.error("Could not activate suction cup, HTTP response {}", response.value());
            throw new BpmnError("Could not activate suction cup");
        }

        response = restClient.post()
                .uri("/move-relative")
                .body(new RelativeMovementCommandDto(zPickup))
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if (response.value() != 200) {
            log.error("Could not move pickup position, HTTP response {}", response.value());
            throw new BpmnError("Could not move to pickup position");
        }

        response = restClient.post()
                .uri("/move-relative")
                .body(new RelativeMovementCommandDto(40f))
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if (response.value() != 200) {
            log.error("Could not pick up block, HTTP response {}", response.value());
            throw new BpmnError("Could not pick up block");
        }
        log.info("Picked up block, moving to holding position");

        toHoldingPosition();
        wait(Duration.ofSeconds(2));
    }

    @Override
    public void toColor() {
        var response = restClient.post()
                .uri("/run-flow?filename=" + config.flows().toColorSensor())
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if (response.value() != 200) {
            log.error("Could not move to color sensor, HTTP response {}", response.value());
            throw new BpmnError("Could not move to color sensor");
        }
        wait(Duration.ofSeconds(2));
    }

    @Override
    public void toDistanceSensor() {
        var response = restClient.post()
                .uri("/run-flow?filename=" + config.flows().toDistanceSensor())
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if (response.value() != 200) {
            log.error("Could not move to distance sensor, HTTP response {}", response.value());
            throw new BpmnError("Could not move to distance sensor");
        }
    }

    @Override
    public void toDiscard() {
        log.warn("To discard not implemented");
    }

    @Override
    public void toAssembly(AssemblyPositionDto position) {
        var response = restClient.post()
                .uri("/run-flow?filename=" + config.flows().toBuildArea())
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if (response.value() != 200) {
            log.error("Could not move to assembly position, HTTP response {}", response.value());
            throw new BpmnError("Could not move to assembly position");
        }

        final var xOffset = config.assembly().cubeSize() * position.x();
        final var zOffset = -config.assembly().zInitial() + config.assembly().cubeSize() * position.z();
        response = restClient.post()
                .uri("/move-relative")
                .body(new RelativeMovementCommandDto(xOffset, 0f))
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if (response.value() != 200) {
            log.error("Could not place block in build area, HTTP response {}", response.value());
            throw new BpmnError("Could not place block in build area");
        }
        response = restClient.post()
                .uri("/move-relative")
                .body(new RelativeMovementCommandDto(zOffset))
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if (response.value() != 200) {
            log.error("Could not place block in build area, HTTP response {}", response.value());
            throw new BpmnError("Could not place block in build area");
        }
        response = restClient.put()
                .uri("/suction-cup")
                .body(new SuctionCupCommandDto(false))
                .retrieve()
                .toBodilessEntity()
                .getStatusCode();
        if (response.value() != 200) {
            log.error("Could not deactivate suction cup, HTTP response {}", response.value());
            throw new BpmnError("Could not deactivate suction cup");
        }
        wait(Duration.ofSeconds(2));
        toHoldingPosition();
    }

    private void wait(Duration duration) {
        try {
            Thread.sleep(duration);
        } catch (Exception ex) {
            log.error("Wait interrupted");
        }
    }
}
