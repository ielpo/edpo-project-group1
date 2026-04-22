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
cd services/dobot-control
uv run src/app.py --robot=left
```

You can select the right or left robot with the commandline parameter.
A simulation mode is available with the `-s` flag.
When running in simulation mode, `DobotFake` can forward commands and sensor reads to
the simulated factory service by reading `simulator.url` from [config.yml](./config.yml)
or the `SIMULATOR_URL` environment variable.

---

## How to Use the REST API

Refer to the [Bruno](https://www.usebruno.com/) environment for examples and prepared requests.

### Endpoints
Base URL right robot: `http://localhost:8200`
Base URL left robot: `http://localhost:8201`

| Method | Endpoint       | Description                                                                |
|--------|----------------|----------------------------------------------------------------------------|
| PUT    | /home          | Home the Robot                                                             |
| PUT    | /move          | Move to absolute coordinates                                               |
| POST   | /move-relative | Move relative to current position                                          |
| PUT    | /set-speed     | Set the Robot speed and optionally acceleration                            |
| PUT    | /stop          | Stop the movement of the Robot (sets speed to 0)                           |
| POST   | /run-flow      | Run a flow, either from a file or passed as request body                   |
| PUT    | /run-conveyor  | Set the direction and speed of the conveyor, or stop it                    |
| POST   | /move-conveyor | Move the conveyor a certain distance in one direction with the given speed |
| GET    | /read-color    | Read the color using the Dobot color sensor                                | 
| GET    | /read-ir       | Check if the IR sensor is detecting an object (sensor on conveyor belt)    |
| PUT    | /suction-cup   | Control suction cup (on/off)                                               |

### Data Structures

**Movement Command**
```json
{
  "x": 0.0,               // float: X coordinate
  "y": 0.0,               // float: Y coordinate
  "z": 0.0,               // float: Z coordinate
  "r": 0.0,               // float: Rotation
  "mode": "MOVE_LINEAR"   // optional string: One of "MOVE_LINEAR", "MOVE_JOINT", "JUMP"
}
```

**RelativeMovementCommand**
```json
{
  "x": 0.0,               // float (optional): Relative X movement
  "y": 0.0,               // float (optional): Relative Y movement
  "z": 0.0,               // float (optional): Relative Z movement
  "r": 0.0                // float (optional): Relative rotation movement
}
```

**RunConveyorCommand**
```json
{
  "direction": "FORWARD", // string: One of "STOP", "FORWARD", "REVERSE"
  "speed": 0.0            // float: Conveyor speed
}
```

**MoveConveyorCommand**
```json
{
  "direction": "FORWARD", // string: One of "STOP", "FORWARD", "REVERSE"
  "speed": 0.0,           // float: Conveyor speed
  "distance": 0.0         // float: Distance to move
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
This endpoint executes a list of commands as specified above, either from a file `/run-flow?filename=my_filename.yaml` or as body of the request.

The YAML must have the following structure, each command is executed in sequence.
Each list entry must be a single-key object where the key is the command type:
```yaml
- MovementCommand:
  x: 200.0
  y: 0.0
  z: 50.0
  r: 0.0
  mode: MOVE_LINEAR

- SuctionCupCommand:
  suck: true

- MovementCommand:
  x: 200.0
  y: 100.0
  z: 50.0
  r: 0.0
  mode: MOVE_JOINT

- SuctionCupCommand:
  suck: false
  
- MoveConveyorCommand:
  direction: FORWARD
  speed: 50.0
  distance: 100.0
```