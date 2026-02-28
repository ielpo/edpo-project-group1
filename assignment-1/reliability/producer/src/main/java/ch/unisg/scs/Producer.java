package ch.unisg.scs;

import com.google.common.io.Resources;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.DeleteTopicsResult;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.awaitility.Awaitility;

import java.io.InputStream;
import java.time.Duration;
import java.util.*;

@Slf4j
public class Producer {

    public static void main(String[] args) {

        String topic = "events";
        final int numPartitions = 1;
        final short replicationFactor = 2;

        var random = new Random();
        var scanner = new Scanner(System.in);

        Properties properties;
        try (InputStream props = Resources.getResource("producer.properties").openStream()) {
            properties = new Properties();
            properties.load(props);

            try (KafkaProducer<String, Gaze> producer = new KafkaProducer<>(properties)) {
//                deleteTopic(topic, properties);
                createTopic(topic, numPartitions, replicationFactor, properties);

                log.info("Enter to start publishing");
                scanner.nextLine();

                for (int counter = 0; ; counter++) {
                    Awaitility.await().atLeast(Duration.ofMillis(100));

                    var deviceID = String.valueOf(random.nextInt(numPartitions));
                    Gaze gazeEvent = new Gaze(counter, System.currentTimeMillis(), random.nextInt(1920), random.nextInt(1080), random.nextInt(2, 6));
                    producer.send(new ProducerRecord<>(
                            topic, // topic
                            deviceID, // key
                            gazeEvent  // value
                    )).get();
                    log.info("gazeEvent sent: {} from deviceID: {}", gazeEvent, deviceID);
                }
            }
        } catch (Throwable throwable) {
            log.error(Arrays.toString(throwable.getStackTrace()));
        }
    }

    /*
    Create topic
     */
    private static void createTopic(String topicName, int numPartitions, short replicationFactor, Properties properties) throws Exception {
        try (AdminClient admin = AdminClient.create(properties)) {
            //checking if topic already exists
            boolean alreadyExists = admin.listTopics().names().get().stream()
                    .anyMatch(existingTopicName -> existingTopicName.equals(topicName));
            if (alreadyExists) {
                log.warn("Topic already exits: {}", topicName);
            } else {
                //creating new topic
                log.info("Creating topic: {}", topicName);
                NewTopic newTopic = new NewTopic(topicName, numPartitions, replicationFactor);
                admin.createTopics(Collections.singleton(newTopic)).all().get();
            }
        }
    }

    /*
    Delete topic
     */
    private static void deleteTopic(String topicName, Properties properties) {
        try (AdminClient client = AdminClient.create(properties)) {
            DeleteTopicsResult deleteTopicsResult = client.deleteTopics(Collections.singleton(topicName));
            Awaitility.await().atMost(Duration.ofSeconds(10)).until(() -> deleteTopicsResult.all().isDone());
        }
    }

}
