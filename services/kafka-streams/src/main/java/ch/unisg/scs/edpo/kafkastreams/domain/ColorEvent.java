package ch.unisg.scs.edpo.kafkastreams.domain;

// Raw RGB reading published to sensor.color.raw.v1 by the color sensor.
// The factory service activates the sensor per block, passing the cubeId so it can be attached to each reading.
// Key: cubeId
public record ColorEvent(
        String cubeId,
        int r,
        int g,
        int b
) {}
