from __future__ import annotations

import logging
from pathlib import Path

from fastapi.testclient import TestClient

from simulated_factory.api import create_app
from simulated_factory.events import EventStore


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yml"


def test_create_app_exposes_engine_and_event_store() -> None:
    app = create_app(str(CONFIG_PATH))
    assert hasattr(app.state, "engine")
    assert hasattr(app.state, "event_store")
    assert isinstance(app.state.event_store, EventStore)


def test_health_and_status_endpoints_are_available() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

    r2 = client.get("/api/status")
    assert r2.status_code == 200
    body = r2.json()
    assert "status" in body

    # events endpoint should exist and return an items list
    r3 = client.get("/api/events")
    assert r3.status_code == 200
    payload = r3.json()
    assert "items" in payload and isinstance(payload["items"], list)
