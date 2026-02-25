"""Tests for respyra.core.target_generator — pure math, no mocking needed."""

from __future__ import annotations

import math

import pytest

from respyra.core.target_generator import (
    ConditionDef,
    SegmentDef,
    TargetGenerator,
    calibrate_from_baseline,
)

# ================================================================
# SegmentDef
# ================================================================


class TestSegmentDef:
    def test_duration_basic(self):
        seg = SegmentDef(freq_hz=0.1, n_cycles=3)
        assert seg.duration == pytest.approx(30.0)

    def test_duration_fast_frequency(self):
        seg = SegmentDef(freq_hz=0.5, n_cycles=2)
        assert seg.duration == pytest.approx(4.0)

    def test_duration_single_cycle(self):
        seg = SegmentDef(freq_hz=0.3, n_cycles=1)
        assert seg.duration == pytest.approx(1.0 / 0.3)

    def test_duration_high_frequency(self):
        seg = SegmentDef(freq_hz=1.0, n_cycles=10)
        assert seg.duration == pytest.approx(10.0)


# ================================================================
# ConditionDef
# ================================================================


class TestConditionDef:
    def test_total_duration_single_segment(self, simple_condition):
        assert simple_condition.total_duration == pytest.approx(30.0)

    def test_total_duration_multi_segment(self, multi_segment_condition):
        # 3/0.1 + 1/0.3 = 30 + 3.333... = 33.333...
        expected = 30.0 + 1.0 / 0.3
        assert multi_segment_condition.total_duration == pytest.approx(expected)

    def test_total_duration_empty_segments(self):
        cond = ConditionDef(name="empty")
        assert cond.total_duration == pytest.approx(0.0)

    def test_default_feedback_gain(self, simple_condition):
        assert simple_condition.feedback_gain == 1.0

    def test_custom_feedback_gain(self, simple_segment):
        cond = ConditionDef(name="perturbed", segments=[simple_segment], feedback_gain=1.5)
        assert cond.feedback_gain == 1.5


# ================================================================
# calibrate_from_baseline
# ================================================================


class TestCalibrateFromBaseline:
    def test_normal_range(self):
        samples = [2.0, 4.0, 6.0, 8.0, 10.0]
        center, amplitude = calibrate_from_baseline(samples)
        assert center == pytest.approx(6.0)  # (2+10)/2
        assert amplitude == pytest.approx(4.0)  # (10-2)/2

    def test_empty_returns_fallback(self):
        center, amplitude = calibrate_from_baseline([])
        assert center == pytest.approx(5.0)
        assert amplitude == pytest.approx(2.0)

    def test_single_value_clamps_to_min_amplitude(self):
        center, amplitude = calibrate_from_baseline([7.0])
        assert center == pytest.approx(7.0)
        assert amplitude == pytest.approx(0.5)  # default min_amplitude

    def test_identical_values_clamps_to_min_amplitude(self):
        center, amplitude = calibrate_from_baseline([5.0, 5.0, 5.0])
        assert center == pytest.approx(5.0)
        assert amplitude == pytest.approx(0.5)

    def test_custom_min_amplitude(self):
        center, amplitude = calibrate_from_baseline([5.0, 5.0], min_amplitude=1.0)
        assert amplitude == pytest.approx(1.0)

    def test_small_range_uses_min_amplitude(self):
        # Range = 0.2, half-range = 0.1 < default min_amplitude 0.5
        center, amplitude = calibrate_from_baseline([4.9, 5.1])
        assert center == pytest.approx(5.0)
        assert amplitude == pytest.approx(0.5)

    def test_negative_values(self):
        samples = [-3.0, -1.0]
        center, amplitude = calibrate_from_baseline(samples)
        assert center == pytest.approx(-2.0)
        assert amplitude == pytest.approx(1.0)

    def test_large_range(self):
        samples = [0.0, 100.0]
        center, amplitude = calibrate_from_baseline(samples)
        assert center == pytest.approx(50.0)
        assert amplitude == pytest.approx(50.0)


# ================================================================
# TargetGenerator
# ================================================================


class TestTargetGenerator:
    def test_at_t_zero_returns_center(self, simple_condition):
        gen = TargetGenerator(simple_condition, center=5.0, amplitude=2.0)
        # sin(0) = 0, so target = center
        assert gen.get_target(0.0) == pytest.approx(5.0)

    def test_quarter_period_returns_center_plus_amplitude(self, simple_condition):
        gen = TargetGenerator(simple_condition, center=5.0, amplitude=2.0)
        # At t = T/4 (quarter period of 0.1 Hz = 2.5s), sin(pi/2) = 1
        assert gen.get_target(2.5) == pytest.approx(7.0)

    def test_half_period_returns_center(self, simple_condition):
        gen = TargetGenerator(simple_condition, center=5.0, amplitude=2.0)
        # At t = T/2 (5s), sin(pi) ≈ 0
        assert gen.get_target(5.0) == pytest.approx(5.0, abs=1e-10)

    def test_three_quarter_period_returns_center_minus_amplitude(self, simple_condition):
        gen = TargetGenerator(simple_condition, center=5.0, amplitude=2.0)
        # At t = 3T/4 (7.5s), sin(3pi/2) = -1
        assert gen.get_target(7.5) == pytest.approx(3.0)

    def test_full_period_returns_center(self, simple_condition):
        gen = TargetGenerator(simple_condition, center=5.0, amplitude=2.0)
        # At t = T (10s), sin(2pi) ≈ 0
        assert gen.get_target(10.0) == pytest.approx(5.0, abs=1e-10)

    def test_wraps_beyond_total_duration(self, simple_condition):
        gen = TargetGenerator(simple_condition, center=5.0, amplitude=2.0)
        # total_duration = 30s; t=32.5 wraps to t=2.5 (quarter period)
        assert gen.get_target(32.5) == pytest.approx(7.0)

    def test_output_bounded_by_center_plus_minus_amplitude(self, simple_condition):
        gen = TargetGenerator(simple_condition, center=5.0, amplitude=2.0)
        for t in [i * 0.1 for i in range(300)]:
            val = gen.get_target(t)
            assert 3.0 - 1e-10 <= val <= 7.0 + 1e-10

    def test_multi_segment_first_segment(self, multi_segment_condition):
        gen = TargetGenerator(multi_segment_condition, center=5.0, amplitude=2.0)
        # t=2.5 is in first segment (0.1 Hz), quarter period → center + amplitude
        assert gen.get_target(2.5) == pytest.approx(7.0)

    def test_multi_segment_second_segment(self, multi_segment_condition):
        gen = TargetGenerator(multi_segment_condition, center=5.0, amplitude=2.0)
        # First segment ends at 30s; second segment is 0.3 Hz.
        # Quarter period of 0.3 Hz = 1/(0.3*4) ≈ 0.8333s
        # So t = 30 + 0.8333 should give center + amplitude
        t_in_second = 30.0 + 1.0 / (0.3 * 4)
        assert gen.get_target(t_in_second) == pytest.approx(7.0)

    def test_sinusoidal_shape(self, simple_condition):
        """Verify the output matches an explicit sin formula."""
        gen = TargetGenerator(simple_condition, center=10.0, amplitude=3.0)
        for t in [0.0, 1.0, 2.5, 5.0, 7.5, 15.0, 29.9]:
            expected = 10.0 + 3.0 * math.sin(2.0 * math.pi * 0.1 * t)
            assert gen.get_target(t) == pytest.approx(expected)
