package ch.unisg.scs.edpo.factory.adapters.out.dtos;

enum Direction{
    STOP,
    FORWARD,
    REVERSE
}

public record ConveyorCommandDto(Direction direction, float speed, float distance) {
}
