"""Tests for SensorUpdateRequest field validators."""

import pytest

from simulated_factory.models import SensorUpdateRequest


class TestRawColorValidator:
    """Tests for coerce_raw_color."""

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            # CSV string → list[int]
            ("0,128,255", [0, 128, 255]),
            ("10, 20, 30", [10, 20, 30]),
            # Already a list of ints
            ([1, 2, 3], [1, 2, 3]),
            # List of strings
            (["0", "128", "255"], [0, 128, 255]),
            # List with float strings
            (["1.5", "2.9"], [1, 2]),
            # List with float values
            ([1.0, 2.5, 3.9], [1, 2, 3]),
            # Empty / None
            (None, None),
            ("", None),
            ([], None),
            # List with empty strings filtered out
            (["10", "", "20"], [10, 20]),
        ],
    )
    def test_coercion(self, input_val, expected):
        req = SensorUpdateRequest(raw_color=input_val)
        assert req.raw_color == expected


class TestScriptedValuesValidator:
    """Tests for coerce_scripted_values."""

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            # CSV string → list of numbers
            ("5,15,25", [5, 15, 25]),
            ("1.5, 2.5, 3.5", [1.5, 2.5, 3.5]),
            # Already a list
            ([5, 15, 25], [5, 15, 25]),
            ([10, 20.5, 30], [10, 20.5, 30]),
            # List of strings
            (["5", "15", "25"], [5, 15, 25]),
            (["1.5", "2.5"], [1.5, 2.5]),
            # Empty / None
            (None, None),
            ("", None),
            ([], []),
            # List with empty strings filtered out
            (["10", "", "20"], [10, 20]),
        ],
    )
    def test_coercion(self, input_val, expected):
        req = SensorUpdateRequest(scripted_values=input_val)
        assert req.scripted_values == expected


class TestValueValidator:
    """Tests for coerce_value."""

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            # Boolean strings
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("false", False),
            ("False", False),
            # Numeric strings
            ("42", 42),
            ("3.14", 3.14),
            # Empty string → None
            ("", None),
            ("  ", None),
            # Already typed values pass through
            (True, True),
            (False, False),
            (42, 42),
            (3.14, 3.14),
            (None, None),
            # Non-numeric string stays as string
            ("RED", "RED"),
            ("BLUE", "BLUE"),
        ],
    )
    def test_coercion(self, input_val, expected):
        req = SensorUpdateRequest(value=input_val)
        assert req.value == expected
