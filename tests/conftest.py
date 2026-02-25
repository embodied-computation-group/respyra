"""Shared fixtures and mock setup for respyra tests."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

# ------------------------------------------------------------------
# Mock PsychoPy and godirect at import time (before collection).
# This lets tests run in environments where these packages are not
# installed (e.g. CI without PsychoPy).  Must happen at module level,
# NOT in fixtures, because test modules import respyra.core.* at the
# top level which triggers `from psychopy import ...`.
# ------------------------------------------------------------------

_MOCK_MODULES = [
    "psychopy",
    "psychopy.core",
    "psychopy.data",
    "psychopy.event",
    "psychopy.gui",
    "psychopy.monitors",
    "psychopy.visual",
    "godirect",
]

for _mod_name in _MOCK_MODULES:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = MagicMock()


# ------------------------------------------------------------------
# Condition/Segment fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def simple_segment():
    """A single 0.1 Hz, 3-cycle segment (30 s duration)."""
    from respyra.core.target_generator import SegmentDef

    return SegmentDef(freq_hz=0.1, n_cycles=3)


@pytest.fixture()
def simple_condition(simple_segment):
    """A single-segment condition."""
    from respyra.core.target_generator import ConditionDef

    return ConditionDef(name="test_slow", segments=[simple_segment])


@pytest.fixture()
def multi_segment_condition():
    """A two-segment condition (like mixed_rhythm)."""
    from respyra.core.target_generator import ConditionDef, SegmentDef

    return ConditionDef(
        name="test_mixed",
        segments=[
            SegmentDef(freq_hz=0.1, n_cycles=3),
            SegmentDef(freq_hz=0.3, n_cycles=1),
        ],
    )
