"""Tests for runner helper functions."""

from __future__ import annotations

import colorsys

import pytest

from respyra.configs.experiment_config import DotConfig, ExperimentConfig
from respyra.core.runner import (
    _compute_dot_color,
    _force_to_dot_y,
    apply_gain,
    graded_dot_color,
)


class TestApplyGain:
    def test_gain_one_returns_copy(self):
        buf = [1.0, 2.0, 3.0]
        result = apply_gain(buf, 1.0, 2.0)
        assert result == pytest.approx([1.0, 2.0, 3.0])
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

    def test_gain_zero_collapses_to_center(self):
        center = 5.0
        buf = [1.0, 5.0, 9.0]
        result = apply_gain(buf, 0.0, center)
        assert result == pytest.approx([5.0, 5.0, 5.0])

    def test_empty_buffer(self):
        assert apply_gain([], 2.0, 5.0) == []

    def test_works_with_deque(self):
        from collections import deque

        buf = deque([1.0, 2.0, 3.0])
        result = apply_gain(buf, 1.0, 2.0)
        assert isinstance(result, list)
        assert result == pytest.approx([1.0, 2.0, 3.0])


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

    def test_mid_error_is_between_green_and_red(self):
        r, g, b = graded_dot_color(1.5, 3.0)
        # Half error with sqrt curve: t = sqrt(0.5) ≈ 0.707, hue ≈ 0.098
        # Should be orange-ish: r > 0, g > -1 but g < 1
        t = (0.5) ** 0.5
        hue = (1.0 - t) / 3.0
        exp_r, exp_g, exp_b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        assert r == pytest.approx(exp_r * 2 - 1)
        assert g == pytest.approx(exp_g * 2 - 1)
        assert b == pytest.approx(exp_b * 2 - 1)

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


class TestForceToDotY:
    def test_mid_force_maps_to_mid_screen(self):
        y = _force_to_dot_y(5.0, y_min=0.0, y_max=10.0, trace_bottom=-0.5, trace_top=0.5)
        assert y == pytest.approx(0.0)

    def test_min_force_maps_to_bottom(self):
        y = _force_to_dot_y(0.0, y_min=0.0, y_max=10.0, trace_bottom=-0.5, trace_top=0.5)
        assert y == pytest.approx(-0.5)

    def test_max_force_maps_to_top(self):
        y = _force_to_dot_y(10.0, y_min=0.0, y_max=10.0, trace_bottom=-0.5, trace_top=0.5)
        assert y == pytest.approx(0.5)

    def test_below_min_clips_to_bottom(self):
        y = _force_to_dot_y(-5.0, y_min=0.0, y_max=10.0, trace_bottom=-0.5, trace_top=0.5)
        assert y == pytest.approx(-0.5)

    def test_above_max_clips_to_top(self):
        y = _force_to_dot_y(15.0, y_min=0.0, y_max=10.0, trace_bottom=-0.5, trace_top=0.5)
        assert y == pytest.approx(0.5)

    def test_zero_span_returns_midpoint(self):
        y = _force_to_dot_y(5.0, y_min=5.0, y_max=5.0, trace_bottom=-0.5, trace_top=0.5)
        assert y == pytest.approx(0.0)

    def test_quarter_force(self):
        y = _force_to_dot_y(2.5, y_min=0.0, y_max=10.0, trace_bottom=0.0, trace_top=1.0)
        assert y == pytest.approx(0.25)


class TestComputeDotColor:
    def test_graded_mode(self):
        cfg = ExperimentConfig(dot=DotConfig(feedback_mode="graded", graded_max_error_n=3.0))
        color = _compute_dot_color(0.0, cfg)
        # Zero error → green
        assert color == pytest.approx((-1.0, 1.0, -1.0))

    def test_binary_mode_good(self):
        cfg = ExperimentConfig(
            dot=DotConfig(
                feedback_mode="binary", error_threshold_n=1.0, color_good="yellow", color_bad="red"
            )
        )
        color = _compute_dot_color(0.5, cfg)
        assert color == "yellow"

    def test_binary_mode_bad(self):
        cfg = ExperimentConfig(
            dot=DotConfig(
                feedback_mode="binary", error_threshold_n=1.0, color_good="yellow", color_bad="red"
            )
        )
        color = _compute_dot_color(1.5, cfg)
        assert color == "red"

    def test_trinary_mode_good(self):
        cfg = ExperimentConfig(
            dot=DotConfig(
                feedback_mode="trinary",
                error_threshold_n=1.0,
                error_threshold_mid_n=2.0,
                color_good="yellow",
                color_mid="orange",
                color_bad="red",
            )
        )
        assert _compute_dot_color(0.5, cfg) == "yellow"

    def test_trinary_mode_mid(self):
        cfg = ExperimentConfig(
            dot=DotConfig(
                feedback_mode="trinary",
                error_threshold_n=1.0,
                error_threshold_mid_n=2.0,
                color_good="yellow",
                color_mid="orange",
                color_bad="red",
            )
        )
        assert _compute_dot_color(1.5, cfg) == "orange"

    def test_trinary_mode_bad(self):
        cfg = ExperimentConfig(
            dot=DotConfig(
                feedback_mode="trinary",
                error_threshold_n=1.0,
                error_threshold_mid_n=2.0,
                color_good="yellow",
                color_mid="orange",
                color_bad="red",
            )
        )
        assert _compute_dot_color(2.5, cfg) == "red"
