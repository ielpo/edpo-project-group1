import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from commands import Direction, MovementCommand, RunConveyorCommand
from dobot_fake import DobotFake
from simulator_client import SimulatorClient


class _ResponseStub:
    def __init__(self, payload=None):
        self._payload = payload or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class SimulatorClientTests(unittest.TestCase):
    @patch("simulator_client.httpx.post")
    def test_forward_command_serializes_movement(self, httpx_post) -> None:
        httpx_post.return_value = _ResponseStub()
        client = SimulatorClient(
            base_url="http://simulator",
            sensor_timeout_seconds=1.0,
            command_timeout_seconds=1.0,
            logger=logging.getLogger(__name__),
        )

        client.forward_command("left", MovementCommand(x=10, y=20, z=30, r=40))

        httpx_post.assert_called_once()
        _, kwargs = httpx_post.call_args
        assert kwargs["json"] == {
            "type": "move",
            "target": {"x": 10.0, "y": 20.0, "z": 30.0, "r": 40.0},
            "mode": "MOVE_JOINT",
        }

    @patch("simulator_client.httpx.get")
    def test_read_color_maps_payload(self, httpx_get) -> None:
        httpx_get.return_value = _ResponseStub(
            {"color": "BLUE", "raw_color": [0, 0, 1]}
        )
        client = SimulatorClient(
            base_url="http://simulator",
            sensor_timeout_seconds=1.0,
            command_timeout_seconds=1.0,
            logger=logging.getLogger(__name__),
        )

        assert client.read_color("left") == ("BLUE", [0, 0, 1])


class DobotFakeTests(unittest.TestCase):
    def test_fake_forwards_commands_and_reads_simulator_sensors(self) -> None:
        dobot = DobotFake("left")
        dobot.simulator_client = Mock()
        dobot.simulator_client.read_color.return_value = ("GREEN", [0, 1, 0])
        dobot.simulator_client.read_ir.return_value = False

        dobot.execute_dobot_commands(
            [
                MovementCommand(x=55, y=10, z=20, r=0),
                RunConveyorCommand(direction=Direction.FORWARD, speed=35),
            ]
        )

        self.assertEqual(dobot.position.x, 55)
        self.assertEqual(dobot.conveyor_speed, 35)
        self.assertEqual(dobot.read_color(), ("GREEN", [0, 1, 0]))
        self.assertFalse(dobot.read_ir())
        self.assertEqual(dobot.simulator_client.forward_command.call_count, 2)