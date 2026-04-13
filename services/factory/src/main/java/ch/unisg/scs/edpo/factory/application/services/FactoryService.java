package ch.unisg.scs.edpo.factory.application.services;

import ch.unisg.scs.edpo.factory.application.ports.in.AssembleOrderPort;
import ch.unisg.scs.edpo.factory.application.ports.in.RequestItemsFromInventoryPort;
import ch.unisg.scs.edpo.factory.application.ports.out.FetchInventoryPort;
import ch.unisg.scs.edpo.factory.application.ports.out.MoveBlockPort;
import ch.unisg.scs.edpo.factory.application.ports.out.ReadColorPort;
import ch.unisg.scs.edpo.factory.domain.*;
import jakarta.validation.constraints.NotNull;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.jspecify.annotations.NonNull;
import org.springframework.stereotype.Service;
import tools.jackson.databind.ObjectMapper;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@RequiredArgsConstructor
@Service
public class FactoryService implements RequestItemsFromInventoryPort, AssembleOrderPort {
    private static final List<AssemblyPositionDto> CHAIR_ASSEMBLY = List.of(
            new AssemblyPositionDto(0, 0, 0)
    );
    private static final List<AssemblyPositionDto> TABLE_ASSEMBLY = List.of(
            new AssemblyPositionDto(0, 0, 0),
            new AssemblyPositionDto(1, 0, 0)
    );
    private static final List<AssemblyPositionDto> SHELF_ASSEMBLY = List.of(
            new AssemblyPositionDto(0, 0, 0),
            new AssemblyPositionDto(0, 0, 1)
    );
    private static final List<AssemblyPositionDto> CLOSET_ASSEMBLY = List.of(
            new AssemblyPositionDto(0, 0, 0),
            new AssemblyPositionDto(0, 0, 1),
            new AssemblyPositionDto(0, 0, 2)
    );

    private final FetchInventoryPort fetchInventory;
    private final MoveBlockPort moveBlock;
    private final ReadColorPort readColor;
    private final MqttService mqttService;
    private final ObjectMapper objectMapper;

    @Override
    public FetchInventoryDto request(@NonNull OrderDto order) {
        // TODO: handle error cases
        return fetchInventory.getInventoryPositions(order.orderId());
    }

    @Override
    public void assemble(@NotNull List<InventoryPositionDto> positions, @NotNull OrderDto order) {
        moveBlock.initialize();

        // Determine positions of blocks for assembly
        List<AssemblyPositionDto> assembly = new ArrayList<>(switch (order.itemType()) {
            case CHAIR -> CHAIR_ASSEMBLY;
            case TABLE -> TABLE_ASSEMBLY;
            case SHELF -> SHELF_ASSEMBLY;
            case CLOSET -> CLOSET_ASSEMBLY;
        });

        // Gather blocks from inventory and build item
        for (var block : positions) {
            log.info("Picking up block from x:{} y:{}", block.x(), block.y());
            moveBlock.fromInventory(block);
            moveBlock.toDistanceSensor();

            log.info("Verifying block pickup with distance sensor, wait for MQTT message");
            var distanceResponse = mqttService.waitForMessage(Duration.ofSeconds(30));
            var distance = objectMapper.readTree(distanceResponse).get("distance").asFloat();
            log.info("Got distance {}", distance);
            if (distance > 25.0) {
                log.error("No block detected, verify robot vacuum and inventory");
                moveBlock.toDiscard();
                throw new RuntimeException("No block picked up, aborting process");
            }

            log.info("Verifying block color");
            moveBlock.toColor();
            var actualColour = readColor.get();
            if (actualColour != block.color()) {
                moveBlock.toDiscard();
                log.error("Unexpected color: {} instead of {}", actualColour, block.color());
                throw new RuntimeException("Unexpected color, aborting process");
            }
            log.info("Moving block to assembly position");
            moveBlock.toAssembly(assembly.removeFirst());
        }
    }
}
