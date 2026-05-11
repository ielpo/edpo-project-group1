package ch.unisg.scs.edpo.kafkastreams.domain;

// Raw distance reading published continuously to sensor.distance.raw.v1 by the conveyor sensor.
// Key: null
public record DistanceEvent(
        float distance,
        long timestamp
) {}
