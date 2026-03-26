package ch.unisg.scs.edpo.order.application.port.out;

public interface EventPublisherPort {
    void publish(String topic, String key, String payload);
}
