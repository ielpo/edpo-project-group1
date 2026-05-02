from uuid import uuid4
from pathlib import Path
import importlib.util

from fastapi.testclient import TestClient

# Dynamically import the inventory app module by path so tests run from repo root
spec = importlib.util.spec_from_file_location(
    "inventory_main",
    Path(__file__).resolve().parents[1] / "main.py",
)
inventory_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory_mod)
app = inventory_mod.app


def setup_client():
    client = TestClient(app)
    # Ensure clean state before each test
    client.post("/restore")
    return client


def test_get_inventory():
    client = setup_client()
    resp = client.get("/inventory")
    assert resp.status_code == 200
    data = resp.json()
    assert "grid" in data
    assert data["rows"] == 5
    assert data["cols"] == 4


def test_reserve_fetch_restore_flow():
    client = setup_client()
    order_id = str(uuid4())

    # Reserve a single RED block
    resp = client.post(f"/reserve?orderId={order_id}", json={"count": 1, "color": "RED"})
    assert resp.status_code == 200

    # Confirm reservation
    resp = client.get(f"/reserve?orderId={order_id}")
    assert resp.status_code == 200
    positions = resp.json()["positions"]
    assert len(positions) == 1
    assert positions[0]["color"] == "RED"

    # Fetch reserved
    resp = client.post(f"/fetch?orderId={order_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "fetched" in data
    assert len(data["fetched"]) == 1

    # Restore via explicit orderId in body
    resp = client.post("/restore", json={"orderId": order_id})
    assert resp.status_code == 200
    assert "restored" in resp.json()


def test_reserve_invalid_color_returns_400():
    client = setup_client()
    order_id = str(uuid4())
    resp = client.post(f"/reserve?orderId={order_id}", json={"count": 1, "color": "MAGENTA"})
    assert resp.status_code == 400
