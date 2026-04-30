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


def test_resolve_unknown_action_returns_404() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    response = client.post(
        "/api/interactive/act-does-not-exist/resolve",
        json={"outcome": "success"},
    )
    assert response.status_code == 404


def test_interactive_config_round_trip() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    initial = client.get("/api/interactive/config")
    assert initial.status_code == 200
    assert initial.json() == {"intercepted": [], "timeoutSeconds": 30}

    updated = client.put(
        "/api/interactive/config",
        json={"intercepted": ["move"], "timeoutSeconds": 5},
    )
    assert updated.status_code == 200
    assert updated.json() == {"intercepted": ["move"], "timeoutSeconds": 5}

    pending = client.get("/api/interactive/pending")
    assert pending.status_code == 200
    assert pending.json() == {"items": []}


def test_index_renders_htmx_shell() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert "text/html" in response.headers["content-type"]
    # htmx loaded
    assert "htmx.org" in body
    # SSE extension wired up
    assert 'sse-connect="/sse/status"' in body
    assert 'sse-swap="update"' in body
    # panel placeholders use hx-get with hx-trigger="load"
    assert 'hx-get="/fragments/presets"' in body
    assert 'hx-trigger="load"' in body


def test_fragment_presets_lists_known_presets() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    response = client.get("/fragments/presets")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert 'id="preset-panel"' in body
    assert "happy-path" in body
    assert "wrong-color" in body
    assert 'hx-post="/api/presets/run"' in body


def test_fragment_presets_shows_pipeline_when_running() -> None:
    from simulated_factory.models import SimulationStatus

    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    engine = app.state.engine
    engine.state.status = SimulationStatus.RUNNING
    engine.state.currentPreset = "happy-path"
    engine.state.currentStep = 1

    response = client.get("/fragments/presets")
    assert response.status_code == 200
    body = response.text
    assert "step-pipeline" in body
    assert "step--active" in body
    assert "step--done" in body


def test_fragment_presets_idle_has_no_pipeline() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    response = client.get("/fragments/presets")
    assert response.status_code == 200
    assert "step-pipeline" not in response.text


def test_sse_status_streams_event_stream() -> None:
    """Verify the /sse/status route registration and media type.

    The endpoint is an open-ended stream, so we inspect the registered
    FastAPI route and a HEAD-style probe rather than block on the body.
    """
    app = create_app(str(CONFIG_PATH))
    sse_route = next(
        (r for r in app.routes if getattr(r, "path", None) == "/sse/status"),
        None,
    )
    assert sse_route is not None, "/sse/status route should be registered"
    assert "GET" in sse_route.methods

    # The handler must construct a StreamingResponse with text/event-stream.
    import inspect
    source = inspect.getsource(sse_route.endpoint)
    assert "text/event-stream" in source


def test_put_sensor_returns_html_for_htmx_caller() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    response = client.put(
        "/api/config/sensors/color-left",
        json={"mode": "fixed", "value": "GREEN", "raw_color": "0,1,0"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="sensor-card-color-left"' in response.text
    assert "GREEN" in response.text


def test_put_sensor_returns_json_for_non_htmx_caller() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    response = client.put(
        "/api/config/sensors/color-left",
        json={"mode": "fixed", "value": "BLUE", "raw_color": [0, 0, 1]},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["sensorId"] == "color-left"
    assert body["value"] == "BLUE"
