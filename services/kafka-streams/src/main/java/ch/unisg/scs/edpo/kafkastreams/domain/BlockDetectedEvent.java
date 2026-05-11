package ch.unisg.scs.edpo.kafkastreams.domain;

// Published when the operator places a block and presses the button.
// Key on sensor.block-detected.v1: cubeId
public record BlockDetectedEvent(
        String cubeId,
        long timestamp
) {}
