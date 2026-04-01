package ch.unisg.scs.edpo.factory.adapters.out.dtos;

enum GripperState {
    OPEN,
    CLOSE,
    DISABLE,
}

public record GripperCommandDto(GripperState state) {
}
