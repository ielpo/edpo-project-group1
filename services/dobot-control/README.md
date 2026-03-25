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
uv run dobot-api --robot=left
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

