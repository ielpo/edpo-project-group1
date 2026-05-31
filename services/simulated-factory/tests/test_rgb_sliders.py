"""Tests for RGB slider and distance slider contract (change: color-sensor-rgb-sliders)."""

import pytest
from starlette.testclient import TestClient

from simulated_factory.api import create_app
from simulated_factory.models import SensorUpdateRequest
from simulated_factory.sensors.color import ColorSensor
from simulated_factory.sensors.distance import DistanceSensor
from simulated_factory.utils import (
    CANONICAL_RGB,
    name_from_raw_color,
    raw_color_from_name,
    rgb_bytes_from_raw,
    validate_distance_range,
    DISTANCE_MIN,
    DISTANCE_MAX,
)

CONFIG_PATH = "config.yml"


# ---------------------------------------------------------------------------
# Utils: canonical named-color mapping
# ---------------------------------------------------------------------------


class TestCanonicalRGB:
    def test_all_canonical_colors_round_trip(self) -> None:
        for name, rgb in CANONICAL_RGB.items():
            assert raw_color_from_name(name) == rgb
            assert name_from_raw_color(rgb) == name

    def test_unknown_color_returns_black(self) -> None:
        assert raw_color_from_name("PURPLE") == [0, 0, 0]

    def test_non_canonical_rgb_returns_none(self) -> None:
        assert name_from_raw_color([128, 50, 0]) is None

    def test_case_insensitive_lookup(self) -> None:
        assert raw_color_from_name("red") == [255, 0, 0]
        assert raw_color_from_name("Green") == [0, 255, 0]


class TestRgbBytesFromRaw:
    def test_passthrough_full_triple(self) -> None:
        assert rgb_bytes_from_raw([100, 200, 50]) == (100, 200, 50)

    def test_clamps_to_0_255(self) -> None:
        assert rgb_bytes_from_raw([-10, 300, 128]) == (0, 255, 128)

    def test_pads_short_list(self) -> None:
        assert rgb_bytes_from_raw([42]) == (42, 0, 0)
        assert rgb_bytes_from_raw([]) == (0, 0, 0)


# ---------------------------------------------------------------------------
# Utils: distance range validation
# ---------------------------------------------------------------------------


class TestDistanceValidation:
    def test_valid_range_returns_value(self) -> None:
        assert validate_distance_range(0.0) == 0.0
        assert validate_distance_range(15.5) == 15.5
        assert validate_distance_range(30.0) == 30.0

    def test_below_min_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_distance_range(-0.1)

    def test_above_max_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_distance_range(30.1)


# ---------------------------------------------------------------------------
# SensorUpdateRequest: r/g/b assembly
# ---------------------------------------------------------------------------


class TestSensorUpdateRequestRGB:
    def test_rgb_fields_assemble_raw_color(self) -> None:
        req = SensorUpdateRequest(r=128, g=64, b=32)
        assert req.raw_color == [128, 64, 32]

    def test_explicit_raw_color_takes_precedence(self) -> None:
        req = SensorUpdateRequest(raw_color=[10, 20, 30], r=200, g=200, b=200)
        assert req.raw_color == [10, 20, 30]

    def test_partial_rgb_fills_zeros(self) -> None:
        req = SensorUpdateRequest(r=100)
        assert req.raw_color == [100, 0, 0]

    def test_no_rgb_no_raw_color(self) -> None:
        req = SensorUpdateRequest(value="RED")
        assert req.raw_color is None


# ---------------------------------------------------------------------------
# ColorSensor: derivation
# ---------------------------------------------------------------------------


class TestColorSensorDerivation:
    def test_apply_canonical_rgb_derives_name(self) -> None:
        sensor = ColorSensor("color-left", {"value": "RED"})
        sensor.apply_update({"raw_color": [0, 0, 255]})
        color, raw = sensor.read()
        assert color == "BLUE"
        assert raw == [0, 0, 255]

    def test_apply_non_canonical_rgb_clears_name(self) -> None:
        sensor = ColorSensor("color-left", {"value": "RED"})
        sensor.apply_update({"raw_color": [128, 64, 32]})
        color, raw = sensor.read()
        # value is None, fallback derives from raw_color → None → "YELLOW" fallback
        assert raw == [128, 64, 32]

    def test_update_by_name_sets_canonical_rgb(self) -> None:
        sensor = ColorSensor("color-left", {"value": "RED"})
        sensor.update("GREEN")
        color, raw = sensor.read()
        assert color == "GREEN"
        assert raw == [0, 255, 0]


# ---------------------------------------------------------------------------
# DistanceSensor: range enforcement
# ---------------------------------------------------------------------------


class TestDistanceSensorRange:
    def test_update_within_range(self) -> None:
        sensor = DistanceSensor("distance-left", {"value": 10.0})
        sensor.update(25.0)
        assert sensor.read() == 25.0

    def test_update_out_of_range_raises(self) -> None:
        sensor = DistanceSensor("distance-left", {"value": 10.0})
        with pytest.raises(ValueError):
            sensor.update(31.0)

    def test_apply_update_out_of_range_raises(self) -> None:
        sensor = DistanceSensor("distance-left", {"value": 10.0})
        with pytest.raises(ValueError):
            sensor.apply_update({"value": -1.0})


# ---------------------------------------------------------------------------
# Preview endpoint
# ---------------------------------------------------------------------------


class TestPreviewEndpoint:
    def test_color_preview_returns_html(self) -> None:
        app = create_app(CONFIG_PATH)
        client = TestClient(app)
        r = client.get("/fragments/sensors/color-left/preview?r=255&g=0&b=0")
        assert r.status_code == 200
        assert "twin-sensor" in r.text
        assert "unsaved" in r.text

    def test_color_preview_shows_custom_swatch(self) -> None:
        app = create_app(CONFIG_PATH)
        client = TestClient(app)
        r = client.get("/fragments/sensors/color-left/preview?r=42&g=100&b=200")
        assert "rgb(42, 100, 200)" in r.text

    def test_distance_preview_returns_html(self) -> None:
        app = create_app(CONFIG_PATH)
        client = TestClient(app)
        r = client.get("/fragments/sensors/distance-left/preview?value=12.5")
        assert r.status_code == 200
        assert "12.5" in r.text
        assert "unsaved" in r.text

    def test_distance_preview_rejects_out_of_range(self) -> None:
        app = create_app(CONFIG_PATH)
        client = TestClient(app)
        r = client.get("/fragments/sensors/distance-left/preview?value=35")
        assert r.status_code == 422

    def test_preview_unknown_sensor_returns_404(self) -> None:
        app = create_app(CONFIG_PATH)
        client = TestClient(app)
        r = client.get("/fragments/sensors/nonexistent/preview?r=0&g=0&b=0")
        assert r.status_code == 404
