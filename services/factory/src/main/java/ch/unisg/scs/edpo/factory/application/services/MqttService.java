package ch.unisg.scs.edpo.factory.application.services;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import jakarta.validation.constraints.NotNull;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.eclipse.paho.client.mqttv3.*;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Arrays;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;

@Slf4j
@RequiredArgsConstructor
@Service
public class MqttService {
    private final Environment environment;
    private final BlockingQueue<MqttMessage> messageQueue;

    private MqttClient client;


    @PostConstruct
    public void start() throws MqttException {
        client = new MqttClient(environment.getRequiredProperty("mqtt.broker-uri"), environment.getRequiredProperty("mqtt.client-id"), new MemoryPersistence());
        client.setCallback(
                new MqttCallback() {
                    @Override
                    public void connectionLost(Throwable throwable) { }

                    @Override
                    public void messageArrived(String topic, MqttMessage message) {
                        //noinspection ResultOfMethodCallIgnored
                        messageQueue.offer(message);
                    }

                    @Override
                    public void deliveryComplete(IMqttDeliveryToken iMqttDeliveryToken) { }
                }
        );
        client.connect();
        client.subscribe(environment.getRequiredProperty("mqtt.topic"));
    }

    @PreDestroy
    public void stop() throws MqttException {
        if (client != null && client.isConnected()) {
            client.disconnect();
        }
    }

    public String waitForMessage(@NotNull Duration timeout) {
        messageQueue.clear();
        try {
            var message = messageQueue.poll(timeout.toMillis(), TimeUnit.MILLISECONDS);
            if (message == null) throw new RuntimeException("Timeout waiting for MQTT message");
            return Arrays.toString(message.getPayload());
        } catch (InterruptedException e) {
            log.error("Interrupted while waiting for MQTT message {}", e.getMessage());
            throw new RuntimeException(e);
        }
    }

}
