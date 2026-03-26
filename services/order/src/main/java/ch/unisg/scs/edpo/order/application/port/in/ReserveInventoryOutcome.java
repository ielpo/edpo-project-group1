package ch.unisg.scs.edpo.order.application.port.in;

public record ReserveInventoryOutcome(
        String orderId,
        String selectedItemType,
        String selectedColor,
        int requiredBlockCount,
        int statusCode,
        String responseBody,
        boolean success,
        String failureType,
        String errorMessage,
        boolean technicalFailure
) {
}
