package ch.unisg.scs.edpo.order.application.port.in;

public record RestoreInventoryOutcome(boolean success, int statusCode, String responseBody, String errorMessage) {
}
