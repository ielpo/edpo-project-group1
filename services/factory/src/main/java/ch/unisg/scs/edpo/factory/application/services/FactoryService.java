package ch.unisg.scs.edpo.factory.application.services;

import ch.unisg.scs.edpo.factory.application.ports.in.RequestItemsFromInventoryPort;
import ch.unisg.scs.edpo.factory.application.ports.out.FetchInventoryPort;
import ch.unisg.scs.edpo.factory.application.ports.out.MoveBlockPort;
import ch.unisg.scs.edpo.factory.application.ports.out.ReadColourPort;
import ch.unisg.scs.edpo.factory.domain.AssemblyPositionDto;
import ch.unisg.scs.edpo.factory.domain.OrderDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.jspecify.annotations.NonNull;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Slf4j
@RequiredArgsConstructor
@Service
public class FactoryService implements RequestItemsFromInventoryPort, AssmebleOrderPort {
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

    @Override
    public void requestItemsFromInventory(@NonNull OrderDto order){

    }

    @Override
    public void assembleOrder(@NonNull OrderDto order) {
        // Fetch inventory information
        var inventory = fetchInventory.getInventoryPositions(order.orderId());
        List<AssemblyPositionDto> assembly = new ArrayList<>(switch(order.itemType()) {
            case Chair -> CHAIR_ASSEMBLY;
            case Table -> TABLE_ASSEMBLY;
            case Shelf -> SHELF_ASSEMBLY;
            case Closet -> CLOSET_ASSEMBLY;
        });

        // Gather blocks from inventory and build item
        for (var block : inventory.positions()) {
            moveBlock.fromInventory(block);
            moveBlock.toColour();
            var actualColour = readColour.get();
            if (actualColour != block.colour()) {
                log.error("Unexpected colour: {} instead of {}", actualColour, block.colour());
                throw new RuntimeException("Unexpected colour");
            }
            moveBlock.toAssembly(assembly.removeFirst());
        }
    }
}
