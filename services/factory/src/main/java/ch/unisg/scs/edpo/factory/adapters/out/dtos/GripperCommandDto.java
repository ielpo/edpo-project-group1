package ch.unisg.scs.edpo.factory.adapters.out.dtos;

public record GripperCommandDto(GripperState state) {
    public enum GripperState {
        OPEN,
        CLOSE,
        DISABLE,
    }
}
