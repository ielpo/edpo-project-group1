package ch.unisg.scs.edpo.factory.domain;

//{"type": "distance_IR_short", "UID": "2a7C", "location": "Conveyor", "messageID": 1273, "distance": 30.0}

import tools.jackson.databind.ObjectMapper;

public record DistanceMeasurementDto(String type, String UID, String location, long messageID, double distance) {
    public static DistanceMeasurementDto fromJson(String json){
        try {
            ObjectMapper mapper = new ObjectMapper();
            return mapper.readValue(json, DistanceMeasurementDto.class);
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse JSON", e);
        }
    }
}

