package ch.unisg.scs.edpo.kafkastreams.domain;

// Emitted after 3 s of wall-clock inactivity on the left distance sensor.
// Published on the internal/diagnostic sensor.block-detected.v1 topic.
// Topic key: "sliding-window-join". The block identifier stays in the payload as cubeId.
public record BlockDetectedEvent(
        String cubeId,
        long timestamp
) {}
