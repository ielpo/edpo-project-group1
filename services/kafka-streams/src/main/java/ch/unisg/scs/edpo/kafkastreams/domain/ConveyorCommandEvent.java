package ch.unisg.scs.edpo.kafkastreams.domain;

public record ConveyorCommandEvent(String command, String triggerId, long timestamp) {
}

