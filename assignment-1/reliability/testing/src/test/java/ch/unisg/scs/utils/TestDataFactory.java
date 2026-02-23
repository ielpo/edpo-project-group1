package ch.unisg.scs.utils;

import ch.unisg.scs.Clicks;
import ch.unisg.scs.Gaze;

import java.util.Random;

/**
 * Factory class for creating test data (Gaze and Click events).
 */
public class TestDataFactory {

    private static final Random random = new Random();

    /**
     * Create a random Gaze event.
     * @param eventID event ID
     * @return Gaze object with random data
     */
    public static Gaze createGazeEvent(int eventID) {
        return new Gaze(
            eventID,
            System.currentTimeMillis(),
            getRandomNumber(0, 1920),
            getRandomNumber(0, 1080),
            getRandomNumber(2, 5)
        );
    }

    /**
     * Create a Gaze event with specific coordinates.
     * @param eventID event ID
     * @param xPosition x coordinate
     * @param yPosition y coordinate
     * @return Gaze object
     */
    public static Gaze createGazeEvent(int eventID, int xPosition, int yPosition) {
        return new Gaze(
            eventID,
            System.currentTimeMillis(),
            xPosition,
            yPosition,
            getRandomNumber(2, 5)
        );
    }

    /**
     * Create a Gaze event with all specified parameters.
     * @param eventID event ID
     * @param timestamp timestamp
     * @param xPosition x coordinate
     * @param yPosition y coordinate
     * @param pupilSize pupil size
     * @return Gaze object
     */
    public static Gaze createGazeEvent(int eventID, long timestamp, int xPosition, int yPosition, int pupilSize) {
        return new Gaze(eventID, timestamp, xPosition, yPosition, pupilSize);
    }

    /**
     * Create a random Click event.
     * @param eventID event ID
     * @return Clicks object with random data
     */
    public static Clicks createClickEvent(int eventID) {
        return new Clicks(
            eventID,
            System.currentTimeMillis(),
            getRandomNumber(0, 1920),
            getRandomNumber(0, 1080),
            getRandomBoolean() ? "LEFT" : "RIGHT"
        );
    }

    /**
     * Create a Click event with specific parameters.
     * @param eventID event ID
     * @param xPosition x coordinate
     * @param yPosition y coordinate
     * @param buttonType button type (LEFT or RIGHT)
     * @return Clicks object
     */
    public static Clicks createClickEvent(int eventID, int xPosition, int yPosition, String buttonType) {
        return new Clicks(eventID, System.currentTimeMillis(), xPosition, yPosition, buttonType);
    }

    /**
     * Create a Click event with all specified parameters.
     * @param eventID event ID
     * @param timestamp timestamp
     * @param xPosition x coordinate
     * @param yPosition y coordinate
     * @param buttonType button type
     * @return Clicks object
     */
    public static Clicks createClickEvent(int eventID, long timestamp, int xPosition, int yPosition, String buttonType) {
        return new Clicks(eventID, timestamp, xPosition, yPosition, buttonType);
    }

    /**
     * Generate a random number within a range.
     * @param min minimum value (inclusive)
     * @param max maximum value (exclusive)
     * @return random number
     */
    public static int getRandomNumber(int min, int max) {
        return random.nextInt(max - min) + min;
    }

    /**
     * Generate a random boolean.
     * @return random boolean
     */
    public static boolean getRandomBoolean() {
        return random.nextBoolean();
    }

    /**
     * Generate a device ID (0-2 for 3 partitions).
     * @return device ID
     */
    public static int getRandomDeviceId() {
        return getRandomNumber(0, 3);
    }

    /**
     * Generate a device ID within a specific range.
     * @param min minimum device ID
     * @param max maximum device ID
     * @return device ID
     */
    public static int getDeviceId(int min, int max) {
        return getRandomNumber(min, max);
    }
}

