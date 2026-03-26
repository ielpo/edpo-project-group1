package ch.unisg.scs.edpo.order.application.port.in;

public interface EventCorrelationUseCase {
    boolean correlateOrderComplete(CorrelateEventCommand command);

    boolean correlateError(CorrelateEventCommand command);
}
