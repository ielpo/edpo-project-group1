package ch.unisg.scs.edpo.order.application.service;

import ch.unisg.scs.edpo.order.application.port.in.InventoryWorkflowUseCase;
import ch.unisg.scs.edpo.order.application.port.in.ReserveInventoryCommand;
import ch.unisg.scs.edpo.order.application.port.in.ReserveInventoryOutcome;
import ch.unisg.scs.edpo.order.application.port.in.RestoreInventoryCommand;
import ch.unisg.scs.edpo.order.application.port.in.RestoreInventoryOutcome;
import ch.unisg.scs.edpo.order.application.port.out.ReserveInventoryPort;
import ch.unisg.scs.edpo.order.application.port.out.ReserveInventoryResult;
import ch.unisg.scs.edpo.order.application.port.out.RestoreInventoryPort;
import ch.unisg.scs.edpo.order.application.port.out.RestoreInventoryResult;
import ch.unisg.scs.edpo.order.domain.BlockColor;
import ch.unisg.scs.edpo.order.domain.ItemType;
import ch.unisg.scs.edpo.order.domain.ReserveInventoryDto;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Locale;
import java.util.UUID;

@Service
public class InventoryWorkflowService implements InventoryWorkflowUseCase {

    @Value("${edpo.inventory.url:http://localhost:8103}")
    private String DEFAULT_URL;

    private final ReserveInventoryPort reserveInventoryPort;
    private final RestoreInventoryPort restoreInventoryPort;

    public InventoryWorkflowService(ReserveInventoryPort reserveInventoryPort, RestoreInventoryPort restoreInventoryPort) {
        this.reserveInventoryPort = reserveInventoryPort;
        this.restoreInventoryPort = restoreInventoryPort;
    }

    @Override
    public ReserveInventoryOutcome reserveInventory(ReserveInventoryCommand command) {
        String url = normalizeUrl(command.inventoryServiceUrl());
        String orderId = resolveOrderId(command.existingOrderId(), command.processBusinessKey());

        try {
            ItemType itemType = parseItemType(command.selectedItem());
            BlockColor color = parseBlockColor(command.selectedColor());
            int requiredBlockCount = requiredBlockCount(itemType);

            ReserveInventoryResult result = reserveInventoryPort.reserve(url,
                    new ReserveInventoryDto(orderId, requiredBlockCount, color));

            boolean success = result.statusCode() >= 200 && result.statusCode() < 300;
            if (success) {
                return new ReserveInventoryOutcome(
                        orderId,
                        itemType.name(),
                        color.name(),
                        requiredBlockCount,
                        result.statusCode(),
                        result.body(),
                        true,
                        null,
                        null,
                        false
                );
            }

            String failureType = result.statusCode() == 409
                    ? "INSUFFICIENT_BLOCKS"
                    : "TECHNICAL_OR_INVALID_REQUEST";
            return new ReserveInventoryOutcome(
                    orderId,
                    itemType.name(),
                    color.name(),
                    requiredBlockCount,
                    result.statusCode(),
                    result.body(),
                    false,
                    failureType,
                    "Inventory service returned status " + result.statusCode(),
                    result.statusCode() != 409
            );
        } catch (IllegalArgumentException e) {
            return new ReserveInventoryOutcome(
                    orderId,
                    null,
                    null,
                    0,
                    0,
                    "",
                    false,
                    "TECHNICAL_OR_INVALID_REQUEST",
                    e.getMessage(),
                    true
            );
        } catch (Exception e) {
            return new ReserveInventoryOutcome(
                    orderId,
                    null,
                    null,
                    0,
                    0,
                    "",
                    false,
                    "TECHNICAL_OR_INVALID_REQUEST",
                    e.getMessage(),
                    true
            );
        }
    }

    @Override
    public RestoreInventoryOutcome restoreInventory(RestoreInventoryCommand command) {
        String url = normalizeUrl(command.inventoryServiceUrl());
        String orderId = command.orderId();

        if (orderId == null || orderId.isBlank()) {
            return new RestoreInventoryOutcome(false, 0, "", "Missing orderId");
        }

        try {
            RestoreInventoryResult result = restoreInventoryPort.restore(url, orderId);
            boolean success = result.statusCode() >= 200 && result.statusCode() < 300;
            String error = success ? null : "Inventory restore failed with status " + result.statusCode() + ": " + result.body();
            return new RestoreInventoryOutcome(success, result.statusCode(), result.body(), error);
        } catch (Exception e) {
            return new RestoreInventoryOutcome(false, 0, "", e.getMessage());
        }
    }

    private String normalizeUrl(String configuredUrl) {
        return configuredUrl == null || configuredUrl.isBlank() ? DEFAULT_URL : configuredUrl;
    }

    private ItemType parseItemType(String value) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("Invalid select_item value: " + value);
        }
        try {
            return ItemType.valueOf(value);
        } catch (IllegalArgumentException e) {
            return ItemType.valueOf(value.trim().toUpperCase(Locale.ROOT));
        }
    }

    private BlockColor parseBlockColor(String value) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("Invalid select_color value: " + value);
        }
        try {
            return BlockColor.valueOf(value);
        } catch (IllegalArgumentException e) {
            return BlockColor.valueOf(value.trim().toUpperCase(Locale.ROOT));
        }
    }

    private int requiredBlockCount(ItemType itemType) {
        return switch (itemType) {
            case CHAIR -> 1;
            case TABLE, SHELF -> 2;
            case CLOSET -> 3;
        };
    }

    private String resolveOrderId(String existingOrderId, String processBusinessKey) {
        if (existingOrderId != null && !existingOrderId.isBlank()) {
            return existingOrderId;
        }
        if (processBusinessKey != null && !processBusinessKey.isBlank()) {
            return processBusinessKey;
        }
        return UUID.randomUUID().toString();
    }
}
