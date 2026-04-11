package ch.unisg.scs.edpo.factory.adapters.out.dtos;

public record ConveyorCommandDto(Direction direction, float speed, float distance) {
    public enum Direction{
        STOP,
        FORWARD,
        REVERSE
    }
}
