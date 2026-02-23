package ch.unisg.scs;

import com.google.common.io.Resources;
import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.DeleteTopicsResult;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;

import java.io.InputStream;
import java.util.*;


public class Producer {

    public static void main(String[] args) throws  Exception {

        // Specify Topic
        String topic = "gaze-events";

        // read Kafka properties file
        Properties properties;
        try (InputStream props = Resources.getResource("producer.properties").openStream()) {
            properties = new Properties();
            properties.load(props);
        }

        // create Kafka producer

        /// delete existing topic with the same name

        // create new topic with 3 partitions
        final int numPartitions = 3;

        try (KafkaProducer<String, Gaze> producer = new KafkaProducer<>(properties)) {
            deleteTopic(topic, properties);
            createTopic(topic, numPartitions, properties);

            // define a counter which will be used as an eventID
            for (int counter = 0; ; counter++) {

                try {
                    Thread.sleep(200);

                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }

                // select random device
                int deviceID = getRandomNumber(0, numPartitions);

                // generate a random gaze event using constructor  Gaze(int eventID, long timestamp, int xPosition, int yPosition, int pupilSize)
                Gaze gazeEvent = new Gaze(counter, System.nanoTime(), getRandomNumber(0, 1920), getRandomNumber(0, 1080), getRandomNumber(2, 5));

                // send the gaze event
                producer.send(new ProducerRecord<String, Gaze>(
                        topic, // topic
                        String.valueOf(deviceID), // key
                        gazeEvent  // value
                ));

                // print to console
                System.out.println("gazeEvent sent: " + gazeEvent.toString() + " from deviceID: " + deviceID);
            }

        } catch (Throwable throwable) {
            System.out.println(Arrays.toString(throwable.getStackTrace()));
        }
    }

    /*
    Generate a random number
    */
    private static int getRandomNumber(int min, int max) {
        return (int) ((Math.random() * (max - min)) + min);
    }

    /*
    Create topic
     */
    private static void createTopic(String topicName, int numPartitions, Properties properties) throws Exception {

        try (AdminClient admin = AdminClient.create(properties)) {
            //checking if topic already exists
            boolean alreadyExists = admin.listTopics().names().get().stream()
                    .anyMatch(existingTopicName -> existingTopicName.equals(topicName));
            if (alreadyExists) {
                System.out.printf("topic already exits: %s\n", topicName);
            } else {
                //creating new topic
                System.out.printf("creating topic: %s\n", topicName);
                NewTopic newTopic = new NewTopic(topicName, numPartitions, (short) 1);
                admin.createTopics(Collections.singleton(newTopic)).all().get();
            }
        }
    }

    /*
    Delete topic
     */
    private static void deleteTopic(String topicName, Properties properties) {

        try (AdminClient client = AdminClient.create(properties)) {
            DeleteTopicsResult deleteTopicsResult  = client.deleteTopics(Collections.singleton(topicName));
            while (!deleteTopicsResult.all().isDone()) {
                // Wait for future task to complete
            }
        }

    }

}
