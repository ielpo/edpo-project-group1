package ch.unisg.scs.edpo.kafkastreams.domain;

// Emitted once per rising edge detected on the right-side distance sensor.
// Used by PickUpBlockTopology to trigger a PICK_AND_PLACE robot-arm command.
public record BlockPickUpTriggerEvent(String triggerId, long timestamp) {
}

