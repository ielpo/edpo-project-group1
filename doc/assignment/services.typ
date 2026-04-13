= Services

== Dashboard
The dashboard service visualizes the current state of the application: inventory stock, and running flows.
The dashboard service uses choreography.

== Order
The order service is responsible for orchestrating the ordering process.

== Factory
The factory service orchestrates the interactions in the physical world.

== Inventory
Keeps track of available blocks and colors, is responsible for the block-order assignment.

== Dobot Control
Communicates with the Dobot using the serial port, and provides a REST API to send commands.

== Color Sensor
Runs on a RaspberryPi Pico, controls and reads out color using a TDSxxx color sensor.

