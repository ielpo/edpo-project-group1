package ch.unisg.scs.edpo.kafkastreams.domain;

// Published to sensor.color.v1 by the MQTT bridge or factory service when reading the color sensor.
// Key: cubeId (the same UUID assigned when the block was detected on the distance sensor).
// Producer contract: the publisher must set cubeId to match the block session started by the distance sensor.
public record ColorEvent(
        String cubeId,
        int r,
        int g,
        int b
) {}
