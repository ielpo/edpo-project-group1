from pathlib import Path

from fastapi.testclient import TestClient

from simulated_factory.api import create_app


CONFIG_PATH = Path(__file__).resolve().parents[1] / "presets.yml"


def test_status_and_presets_endpoints() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    status_response = client.get("/api/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "idle"

    presets_response = client.get("/api/presets")
    assert presets_response.status_code == 200
    preset_names = [item["name"] for item in presets_response.json()["items"]]
    assert "happy-path" in preset_names


def test_dobot_command_and_sensor_aliases() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    command_response = client.post(
        "/api/dobot/left/commands",
        json={
            "type": "move",
            "target": {"x": 20, "y": 10, "z": 5, "r": 0},
            "mode": "MOVE_LINEAR",
        },
    )
    assert command_response.status_code == 202

    state_response = client.get("/api/dobot/left/state")
    assert state_response.status_code == 200
    assert state_response.json()["position"]["x"] == 20.0

    color_response = client.get("/color")
    assert color_response.status_code == 200
    assert set(color_response.json().keys()) == {"r", "g", "b"}

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
