package ch.unisg.scs.edpo.kafkastreams.domain;

// Raw RGB reading published continuously to sensor.color.raw.v1 by the color sensor.
// Key: null (no block identifier; correlation is done by Kafka Streams via a time window join)
public record ColorEvent(
        int r,
        int g,
        int b
) {}
