package ch.unisg.scs.edpo.kafkastreams.domain;

// Published externally when a block is placed on the conveyor (manual trigger).
// Key on sensor.block-detected.v1: cubeId
public record BlockDetectedEvent(
        String cubeId,
        String sensorUid,
        long timestamp
) {}
