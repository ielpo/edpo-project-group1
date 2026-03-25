# Dobot Magician Control Project

This Python project provides a way to control a Dobot robotic arm. The included Flask application exposes HTTP endpoints that let you calibrate and move the robot, as well as work with JSON-based movement scripts.

---

## Requirements  

- [uv](https://docs.astral.sh/uv/getting-started/installation/) for dependency management and running the application
- Access to a Dobot robotic arm (via USB or serial port)

## Running the Application  

If needed, adapt the configuration in [config.yml](./config.yml)

Install all the dependencies and run the application with
```shell
uv run --directory "services/dobot-control" dobot-api --robot=left
```
You can select the right or left robot with the commandline parameter.

---

## How to Use the REST API

Refer to the [Bruno](https://www.usebruno.com/) environment for examples and prepared requests.

### Endpoints
Base URL left robot: `http://localhost:5000`
Base URL right robot: `http://localhost:5001`

| Method | Endpoint       | Description                                                                |
|--------|----------------|----------------------------------------------------------------------------|
| PUT    | /home          | Home the Robot                                                             |
| PUT    | /change-speed  | Set the Robot speed and optionally acceleration                            |
| PUT    | /stop          | Stop the movement of the Robot (sets speed to 0)                           |
| POST   | /run-flow      | Run a flow, either from a file or passed as request body                   |
| PUT    | /run-conveyor  | Set the direction and speed of the conveyor, or stop it                    |
| POST   | /move-conveyor | Move the conveyor a certain distance in one direction with the given speed |
| GET    | /read-color    | Read the color using the Dobot color sensor                                | 
| GET    | /read-ir       | Check if the IR sensor is detecting an object (sensor on conveyor belt)    |

### Data Structures

**Movement Command**
```json
{
  "x": 0.0,               // float: X coordinate
  "y": 0.0,               // float: Y coordinate
  "z": 0.0,               // float: Z coordinate
  "r": 0.0,               // float: Rotation
  "mode": "MOVE_LINEAR"   // string: One of "MOVE_LINEAR", "MOVE_JOINT", "JUMP"
}
```

**ConveyorCommand**
```json
{
  "direction": "FORWARD", // string: One of "STOP", "FORWARD", "REVERSE"
  "speed": 0.0,           // float: Conveyor speed
  "distance": 0.0         // float: (optional, for move-conveyor) Distance to move
}
```

**SuctionCupCommand**
```json
{
  "suck": true            // boolean: Whether to activate the suction cup
}
```

**GripperCommand**
```json
{
  "state": "OPEN"         // string: One of "OPEN", "CLOSE", "DISABLE"
}
```

**MovementSpeedCommand**
```json
{
  "speed": 0.0,           // float: Speed value
  "acceleration": 0.0     // float (optional): Acceleration value
}
```

**run-flow**
This endpoints executes a list of commands as specified above, either from a file `/run-flow?filename=my_filename.json` or as body of the request.

The JSON must have the following structure, each command is executed in sequence
```json
[ 
  { "type": "MovementCommand", "x": 200.0, "y": 0.0, "z": 50.0, "r": 0.0, "mode": "MOVE_LINEAR" },
  { "type": "SuctionCupCommand", "suck": true },
  { "type": "MovementCommand", "x": 200.0, "y": 100.0, "z": 50.0, "r": 0.0, "mode": "MOVE_JOINT" },
  { "type": "SuctionCupCommand", "suck": false },
  { "type": "ConveyorCommand", "direction": "FORWARD", "speed": 50.0, "distance": 100.0 } 
]
```