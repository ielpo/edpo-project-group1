import argparse
import logging
import os
import xml.etree.ElementTree as ET
import yaml
from flask import Flask, request

from commands import (
    Command,
    MovementSpeedCommand,
    command_type_map,
    SuctionCupCommand,
    MovementCommand,
    RunConveyorCommand,
    MoveConveyorCommand,
    RelativeMovementCommand,
)
from config_model import Config
from dobot import Dobot
from dobot_fake import DobotFake

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.Logger(__name__)

app = Flask(__name__)
dobot: Dobot | None = None


def _parse_xml_flow(content: str) -> list[dict]:
    root = ET.fromstring(content)
    command_list_raw: list[dict] = []
    previous_suction_state: bool | None = None

    for row in root:
        if not row.tag.startswith("row") or not row.tag[3:].isdigit():
            continue

        row_values = {child.tag: (child.text or "").strip() for child in row}
        movement = {
            "x": float(row_values["item_2"]),
            "y": float(row_values["item_3"]),
            "z": float(row_values["item_4"]),
            "r": float(row_values["item_5"]),
        }
        command_list_raw.append({"MovementCommand": movement})

        suction_text = row_values.get("item_12")
        if suction_text:
            suction_state = bool(int(float(suction_text)))
            if (
                previous_suction_state is None
                or suction_state != previous_suction_state
            ):
                command_list_raw.append({"SuctionCupCommand": {"suck": suction_state}})
                previous_suction_state = suction_state

    return command_list_raw


@app.before_request
def log_request_info():
    headers = "\n\t".join(f"{k}: {v}" for k, v in request.headers.items())
    if request.args:
        arguments = "\n\t".join(f"{k}: {v}" for k, v in request.args.items())
    else:
        arguments = None

    body = request.get_data(as_text=True)
    body = body if body else None

    logging.debug(
        f"--- Incoming Request ---\n"
        f"Method: {request.method}\n"
        f"Path: {request.path}\n"
        f"Args:\n{arguments}\n"
        f"Body:\n{body}\n"
        f"Headers:\n    {headers}\n"
        f"-----------------------"
    )


@app.route("/run-flow", methods=["POST"])
def run_flow() -> dict:
    filename = request.args.get("filename")
    if filename:
        file_path = os.path.join(os.getcwd(), "flows", filename)
        with open(file_path, "r") as f:
            flow_content = f.read()
    else:
        flow_content = request.get_data(as_text=True)

    # Default to YAML
    flow_format = "yaml"
    if filename:
        _, ext = os.path.splitext(filename.lower())
        if ext in {".xml", ".playback"}:
            flow_format = "xml"
        if ext in {".yaml", ".yml"}:
            flow_format = "yaml"

    if flow_format == "xml":
        command_list_raw = _parse_xml_flow(flow_content)
    else:
        command_list_raw = yaml.safe_load(flow_content)

    command_list: list[Command] = [
        command_type_map[key].model_validate(value)
        for cmd in command_list_raw
        for key, value in cmd.items()
    ]

    logger.info(f"Executing {len(command_list)} movement commands")
    logger.debug(command_list)

    dobot.execute_dobot_commands(command_list)

    logger.info("Finished executing commands")
    return {"message": "Dobot has finished executing commands."}


@app.route("/move", methods=["PUT"])
def move_robot() -> dict:
    command = MovementCommand.model_validate(request.get_json())
    dobot.execute_dobot_commands([command])
    return {"message": "Absolute movement command executed."}


@app.route("/move-relative", methods=["PUT"])
def relative_move_robot() -> dict:
    command = RelativeMovementCommand.model_validate(request.get_json())
    dobot.execute_dobot_commands([command])
    return {"message": "Relative movement command executed."}


@app.route("/run-conveyor", methods=["PUT"])
def run_conveyor() -> dict:
    command = RunConveyorCommand.model_validate(request.get_json())
    if dobot.name == "left":
        dobot.execute_dobot_commands([command])
        return {"message": "Conveyor speed and direction set."}
    else:
        return {"message": "Right Robot does not control conveyor."}


@app.route("/move-conveyor", methods=["POST"])
def move_conveyor() -> dict:
    command = MoveConveyorCommand.model_validate(request.get_json())
    if dobot.name == "left":
        dobot.execute_dobot_commands([command])
        return {"message": "Conveyor moved."}
    else:
        return {"message": "Right Robot does not control conveyor."}


@app.route("/suction-cup", methods=["PUT"])
def suction_cup_command() -> dict:
    command = SuctionCupCommand.model_validate(request.get_json())
    dobot.execute_dobot_commands([command])
    return {"message": "Suction cup command executed"}


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
        "-r", "--robot", choices=config.robots.keys(), help="Robot to be connected"
    )
    parser.add_argument(
        "-s",
        "--simulation",
        action="store_true",
        help="Enables simulation, when running without robots",
    )
    args = parser.parse_args()

    # Get the selected robot configuration, resort to default if no commandline parameter given
    robot_name = args.robot if args.robot else config.default_robot
    runtime_config = config.robots[robot_name]

    if args.simulation:
        logger.info("Running in simulation mode")
        dobot = DobotFake(robot_name)
    else:
        dobot = Dobot(robot_name, runtime_config.robot_port)

    app.run(host="0.0.0.0", port=runtime_config.server_port, debug=True, threaded=True)


if __name__ == "__main__":
    main()
