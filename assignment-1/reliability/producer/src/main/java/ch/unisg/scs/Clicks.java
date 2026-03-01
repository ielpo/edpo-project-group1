package ch.unisg.scs;

import lombok.Getter;

public class Clicks {

    @Getter
    int eventID;
    @Getter
    long timestamp;
    @Getter
    int xPosition; // position of the click within the x-coordinate of the screen
    @Getter
    int yPosition; // position of the click within the y-coordinate of the screen
    String clickedElement;

    public Clicks(int eventID, long timestamp, int xPosition, int yPosition, String clickedElement) {
        this.eventID = eventID;
        this.timestamp = timestamp;
        this.xPosition = xPosition;
        this.yPosition = yPosition;
        this.clickedElement = clickedElement;
    }

    public String toString() {
        return "eventID: " + eventID + ", " +
                "timestamp: " + timestamp + ", " +
                "xPosition: " + xPosition + ", " +
                "yPosition: " + yPosition + ", " +
                "clickedElement: " + clickedElement + ", ";
    }
}
