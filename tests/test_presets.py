"""Tests for condition preset factories and standard instances."""

from __future__ import annotations

from respyra.configs.presets import (
    MIXED_RHYTHM,
    PERTURBED_SLOW,
    SLOW_STEADY,
    mixed_rhythm,
    perturbed_slow,
    slow_steady,
)
from respyra.core.target_generator import ConditionDef


class TestSlowSteady:
    def test_default(self):
        c = slow_steady()
        assert isinstance(c, ConditionDef)
        assert c.name == "slow_steady"
        assert len(c.segments) == 1
        assert c.segments[0].freq_hz == 0.1
        assert c.segments[0].n_cycles == 3
        assert c.feedback_gain == 1.0

    def test_custom_params(self):
        c = slow_steady(freq_hz=0.15, n_cycles=5)
        assert c.segments[0].freq_hz == 0.15
        assert c.segments[0].n_cycles == 5

    def test_duration(self):
        c = slow_steady(freq_hz=0.1, n_cycles=4)
        assert c.total_duration == 40.0


class TestPerturbedSlow:
    def test_default(self):
        c = perturbed_slow()
        assert c.name == "perturbed_slow"
        assert c.feedback_gain == 1.5
        assert len(c.segments) == 1
        assert c.segments[0].freq_hz == 0.1

    def test_custom_gain(self):
        c = perturbed_slow(feedback_gain=2.5)
        assert c.feedback_gain == 2.5

    def test_custom_cycles(self):
        c = perturbed_slow(n_cycles=4)
        assert c.segments[0].n_cycles == 4


class TestMixedRhythm:
    def test_default(self):
        c = mixed_rhythm()
        assert c.name == "mixed_rhythm"
        assert len(c.segments) == 2
        assert c.segments[0].freq_hz == 0.1
        assert c.segments[0].n_cycles == 3
        assert c.segments[1].freq_hz == 0.3
        assert c.segments[1].n_cycles == 1
        assert c.feedback_gain == 1.0

    def test_custom_params(self):
        c = mixed_rhythm(freq_slow=0.2, cycles_slow=2, freq_fast=0.5, cycles_fast=3)
        assert c.segments[0].freq_hz == 0.2
        assert c.segments[0].n_cycles == 2
        assert c.segments[1].freq_hz == 0.5
        assert c.segments[1].n_cycles == 3


class TestStandardInstances:
    def test_slow_steady_matches_factory(self):
        assert SLOW_STEADY.name == "slow_steady"
        assert SLOW_STEADY.segments[0].freq_hz == 0.1
        assert SLOW_STEADY.segments[0].n_cycles == 3

    def test_perturbed_slow_matches_factory(self):
        assert PERTURBED_SLOW.name == "perturbed_slow"
        assert PERTURBED_SLOW.feedback_gain == 1.5

    def test_mixed_rhythm_matches_factory(self):
        assert MIXED_RHYTHM.name == "mixed_rhythm"
        assert len(MIXED_RHYTHM.segments) == 2
