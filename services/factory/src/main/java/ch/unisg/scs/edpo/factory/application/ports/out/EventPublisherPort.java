package ch.unisg.scs.edpo.factory.application.ports.out;

public interface EventPublisherPort {
    void publish(String topic, String key, String payload);
}
