import json
import logging

from flask import Flask, request

from commands import (
    Command,
    ConveyorCommand,
    MovementSpeedCommand,
    command_type_map,
)
from config_model import Config
from dobot import Dobot

import os
import yaml
import argparse

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s"
)

app = Flask(__name__)
dobot: Dobot | None = None
logger = logging.Logger(__name__)


@app.before_request
def log_request_info():
    logging.debug(
        f"Request: {request.method} {request.path} - Args: {request.args} - Body: {request.get_data(as_text=True)}"
    )


@app.route("/run-flow", methods=["POST"])
def run_flow() -> dict:
    filename = request.args.get("filename")
    if filename:
        file_path = os.path.join(os.getcwd(), filename)
        with open(file_path, "r") as f:
            command_list_json: dict = json.load(f)
    else:
        command_list_json: dict = request.get_json()

    command_list: list[Command] = [
        command_type_map[cmd.type].model_validate(cmd) for cmd in command_list_json
    ]

    logger.info(f"Executing {len(command_list)} movement commands")
    logger.debug(command_list)

    dobot.execute_dobot_commands(command_list)

    logger.info("Finished executing commands")
    return {"message": "Dobot has finished executing commands."}


@app.route("/run-conveyor", methods=["PUT"])
def run_conveyor() -> dict:
    command = ConveyorCommand.model_validate(request.get_json())

    if dobot.name == "left":
        dobot.device.conveyor_belt(command.speed, command.direction)
        return {"message": "Conveyor speed and direction set."}
    else:
        return {"message": "Right Robot does not control conveyor."}


@app.route("/move-conveyor", methods=["POST"])
def move_conveyor() -> dict:
    command = ConveyorCommand.model_validate(request.get_json())

    if dobot.name == "left":
        dobot.device.conveyor_belt_distance(
            command.speed, command.distance, command.direction
        )
        return {"message": "Conveyor change added to queue."}
    else:
        return {"message": "Right Robot does not control conveyor."}


@app.route("/set-speed", methods=["PUT"])
def set_speed() -> dict:
    command = MovementSpeedCommand.model_validate(request.get_json())
    dobot.set_speed(command.speed, command.acceleration)
    return {"message": "Speed changed."}


@app.route("/home", methods=["PUT"])
def home_robot():
    dobot.home()
    return {"message": "Robot homed."}


@app.route("/stop", methods=["PUT"])
def stop_robot():
    dobot.stop_robot()
    return {"message": "Robot stopped."}


@app.route("/read-color", methods=["GET"])
def read_color() -> dict:
    if dobot.name == "left":
        color, raw_color = dobot.read_color()
        return {"color": color, "raw_color": raw_color}
    else:
        return {"message": "Right Robot does not have color sensor."}


@app.route("/read-ir", methods=["GET"])
def read_ir() -> dict:
    if dobot.name == "left":
        ir = dobot.read_ir()
        return {"ir": ir}
    else:
        return {"message": "Right Robot does not have IR sensor."}


def main():
    global dobot
    global app

    with open("config.yml", "r") as file:
        config_dict = yaml.safe_load(file)
        config = Config.model_validate(config_dict)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--robot", choices=config.robots.keys(), help="Robot to be connected"
    )
    args = parser.parse_args()

    # Get the selected robot configuration, resort to default if no commandline parameter given
    robot_name = args.robot if args.robot else config.default_robot
    runtime_config = config.robots[robot_name]
    dobot = Dobot(robot_name, runtime_config.robot_port)

    app.run(host="0.0.0.0", port=runtime_config.server_port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
