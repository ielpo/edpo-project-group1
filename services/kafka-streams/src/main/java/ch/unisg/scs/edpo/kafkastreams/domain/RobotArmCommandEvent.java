package ch.unisg.scs.edpo.kafkastreams.domain;

public record RobotArmCommandEvent(String command, String triggerId, long timestamp) {
}

