package ch.unisg.scs;

import lombok.Getter;

public class Gaze {

    int eventID;
    @Getter
    long timestamp;
    @Getter
    int xPosition; // position of the gaze within the x-coordinate of the screen
    @Getter
    int yPosition; // position of the gaze within the y-coordinate of the screen
    @Getter
    int pupilSize; // size of the eye pupil as captured by the eye-tracker

    public Gaze(int eventID, long timestamp, int xPosition, int yPosition, int pupilSize) {
        this.eventID = eventID;
        this.timestamp = timestamp;
        this.xPosition = xPosition;
        this.yPosition = yPosition;
        this.pupilSize = pupilSize;
    }

    public String toString() {
        return "eventID: " + eventID + ", " +
                "timestamp: " + timestamp + ", " +
                "xPosition: " + xPosition + ", " +
                "yPosition: " + yPosition + ", " +
                "pupilSize: " + pupilSize + ", ";
    }
}
