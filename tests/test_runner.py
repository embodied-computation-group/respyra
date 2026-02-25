"""Tests for runner helper functions."""

from __future__ import annotations

import math

import pytest

from respyra.core.runner import apply_gain, graded_dot_color


class TestApplyGain:
    def test_gain_one_returns_copy(self):
        buf = [1.0, 2.0, 3.0]
        result = apply_gain(buf, 1.0, 2.0)
        assert result == [1.0, 2.0, 3.0]
        assert result is not buf

    def test_gain_two_doubles_deviation(self):
        center = 5.0
        buf = [4.0, 5.0, 6.0]
        result = apply_gain(buf, 2.0, center)
        # 4.0 -> 5.0 + 2.0 * (4.0 - 5.0) = 3.0
        # 5.0 -> 5.0 + 2.0 * (5.0 - 5.0) = 5.0
        # 6.0 -> 5.0 + 2.0 * (6.0 - 5.0) = 7.0
        assert result == pytest.approx([3.0, 5.0, 7.0])

    def test_gain_half_attenuates(self):
        center = 10.0
        buf = [8.0, 10.0, 12.0]
        result = apply_gain(buf, 0.5, center)
        assert result == pytest.approx([9.0, 10.0, 11.0])

    def test_empty_buffer(self):
        assert apply_gain([], 2.0, 5.0) == []

    def test_works_with_deque(self):
        from collections import deque

        buf = deque([1.0, 2.0, 3.0])
        result = apply_gain(buf, 1.0, 2.0)
        assert isinstance(result, list)
        assert result == [1.0, 2.0, 3.0]


class TestGradedDotColor:
    def test_zero_error_is_green(self):
        r, g, b = graded_dot_color(0.0, 3.0)
        # Green in PsychoPy: (-1, 1, -1)
        assert r == pytest.approx(-1.0)
        assert g == pytest.approx(1.0)
        assert b == pytest.approx(-1.0)

    def test_max_error_is_red(self):
        r, g, b = graded_dot_color(3.0, 3.0)
        # Red in PsychoPy: (1, -1, -1)
        assert r == pytest.approx(1.0)
        assert g == pytest.approx(-1.0)
        assert b == pytest.approx(-1.0)

    def test_beyond_max_clamps_to_red(self):
        r, g, b = graded_dot_color(10.0, 3.0)
        assert r == pytest.approx(1.0)
        assert g == pytest.approx(-1.0)

    def test_negative_error_uses_abs(self):
        color_pos = graded_dot_color(1.5, 3.0)
        color_neg = graded_dot_color(-1.5, 3.0)
        assert color_pos == pytest.approx(color_neg)

    def test_mid_error_is_yellowish(self):
        r, g, b = graded_dot_color(1.5, 3.0)
        # Should be between green and red — r > -1, g > -1
        assert r > -1.0
        assert g > -1.0

    def test_returns_tuple_of_three(self):
        result = graded_dot_color(1.0, 3.0)
        assert len(result) == 3
        assert all(isinstance(v, float) for v in result)

    def test_values_in_psychopy_range(self):
        """All colour values should be in [-1, 1]."""
        for error in [0.0, 0.5, 1.0, 2.0, 3.0, 5.0]:
            r, g, b = graded_dot_color(error, 3.0)
            assert -1.0 <= r <= 1.0
            assert -1.0 <= g <= 1.0
            assert -1.0 <= b <= 1.0
