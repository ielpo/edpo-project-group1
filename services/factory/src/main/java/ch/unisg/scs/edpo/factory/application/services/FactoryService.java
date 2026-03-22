package ch.unisg.scs.edpo.factory.application.services;

import ch.unisg.scs.edpo.factory.application.ports.in.AssembleOrderPort;
import ch.unisg.scs.edpo.factory.application.ports.in.RequestItemsFromInventoryPort;
import ch.unisg.scs.edpo.factory.application.ports.out.FetchInventoryPort;
import ch.unisg.scs.edpo.factory.application.ports.out.MoveBlockPort;
import ch.unisg.scs.edpo.factory.application.ports.out.ReadColourPort;
import ch.unisg.scs.edpo.factory.domain.*;
import jakarta.validation.constraints.NotNull;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.jspecify.annotations.NonNull;
import org.springframework.stereotype.Service;

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
            new AssemblyPositionDto(0, 1, 0)
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
    private final ReadColourPort readColour;
    private final MqttService mqttService;

    @Override
    public FetchInventoryDto request(@NonNull OrderDto order) {
        return fetchInventory.getInventoryPositions(order.orderId());
    }

    @Override
    public void assemble(@NotNull List<InventoryPositionDto> positions, @NotNull OrderDto order) {
        // Determine positions of blocks for assembly
        List<AssemblyPositionDto> assembly = new ArrayList<>(switch (order.itemType()) {
            case Chair -> CHAIR_ASSEMBLY;
            case Table -> TABLE_ASSEMBLY;
            case Shelf -> SHELF_ASSEMBLY;
            case Closet -> CLOSET_ASSEMBLY;
        });

        // Gather blocks from inventory and build item
        for (var block : positions) {
            log.info("Picking up block from x:{} y:{}", block.x(), block.y());
            moveBlock.fromInventory(block);
            moveBlock.toDistanceSensor();
            var distance = DistanceMeasurementDto.fromJson(mqttService.waitForMessage(Duration.ofSeconds(30))).distance();
            if (distance > 30.0) {
                moveBlock.toDiscard();
                log.error("No block detected, verify robot vacuum and inventory");
                throw new RuntimeException("No block picked up, aborting process");
            }
            moveBlock.toColor();
            var actualColour = readColour.get();
            if (actualColour != block.colour()) {
                moveBlock.toDiscard();
                log.error("Unexpected colour: {} instead of {}", actualColour, block.colour());
                throw new RuntimeException("Unexpected colour, aborting process");
            }
            moveBlock.toAssembly(assembly.removeFirst());
        }
    }
}
