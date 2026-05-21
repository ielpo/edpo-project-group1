"""Tests for the factory digital twin: inventory cache + twin fragment."""

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from simulated_factory.adapters.distance_publisher import DistancePublisher
from simulated_factory.api import create_app
from simulated_factory.engine import SimulationEngine
from simulated_factory.events import EventBridge, EventStore


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yml"
LOGGER = logging.getLogger(__name__)


def _make_engine() -> SimulationEngine:
    event_store = EventStore()
    return SimulationEngine(
        config_path=str(CONFIG_PATH),
        event_store=event_store,
        distance_publisher=DistancePublisher(None, event_store, LOGGER),
        event_bridge=EventBridge("none", None, LOGGER),
    )


# ---------------------------------------------------------------------------
# 7.1 — get_inventory_cache fallback
# ---------------------------------------------------------------------------
def test_get_inventory_cache_returns_neutral_envelope_when_cold() -> None:
    engine = _make_engine()
    assert engine._inventory_cache is None
    cache = engine.get_inventory_cache()
    assert cache == {"grid": None, "rows": 0, "cols": 0}


def test_get_inventory_cache_returns_stored_value() -> None:
    engine = _make_engine()
    engine._inventory_cache = {"grid": [[None]], "rows": 1, "cols": 1}
    cache = engine.get_inventory_cache()
    assert cache == {"grid": [[None]], "rows": 1, "cols": 1}


# ---------------------------------------------------------------------------
# 7.2 — block location badge mapping
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "step_name,expect_in_html",
    [
        (None, None),  # no badge in conveyor or assembly
        ("order-received", None),
        ("pickup", "ON CONVEYOR"),
        ("color-check", "AT PICKUP ZONE"),
        ("place", "BEING PLACED"),
        ("reject", "BEING REJECTED"),
        ("some-unknown-step", "IN PROGRESS"),
    ],
)
def test_twin_fragment_block_location_badge_mapping(
    step_name: str | None, expect_in_html: str | None
) -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    engine = app.state.engine
    engine.state.currentStepName = step_name

    response = client.get("/fragments/twin")
    assert response.status_code == 200
    body = response.text

    if expect_in_html is None:
        assert "ON CONVEYOR" not in body
        assert "AT PICKUP ZONE" not in body
        assert "BEING PLACED" not in body
        assert "BEING REJECTED" not in body
        assert "IN PROGRESS" not in body
    else:
        assert expect_in_html in body


# ---------------------------------------------------------------------------
# 7.3 — /fragments/twin smoke test
# ---------------------------------------------------------------------------
def test_fragment_twin_returns_panel_with_id() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    response = client.get("/fragments/twin")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert 'id="twin-panel"' in body
    # All six factory zones are rendered.
    for zone_id in (
        "twin-zone-inventory",
        "twin-zone-conveyor",
        "twin-zone-robot",
        "twin-zone-color",
        "twin-zone-distance",
        "twin-zone-assembly",
    ):
        assert f'id="{zone_id}"' in body


def test_fragment_twin_renders_unavailable_when_inventory_cache_cold() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    # Engine starts with cache=None; lifespan poller is not started by TestClient
    # context manager unless used as `with TestClient(...)`. So cache is cold here.
    response = client.get("/fragments/twin")
    assert response.status_code == 200
    assert "Unavailable" in response.text


# ---------------------------------------------------------------------------
# 7.4 — /api/inventory smoke test
# ---------------------------------------------------------------------------
def test_api_inventory_returns_neutral_envelope_when_cache_cold() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    response = client.get("/api/inventory")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert set(body.keys()) >= {"grid", "rows", "cols"}
    assert body == {"grid": None, "rows": 0, "cols": 0}


def test_api_inventory_returns_cached_value() -> None:
    app = create_app(str(CONFIG_PATH))
    client = TestClient(app)

    cached = {
        "grid": [[{"color": "RED", "reserved": False, "order_id": None}]],
        "rows": 1,
        "cols": 1,
    }
    app.state.engine._inventory_cache = cached

    response = client.get("/api/inventory")
    assert response.status_code == 200
    assert response.json() == cached
