"""Built-in condition families for common breathing paradigms.

Provides factory functions that return :class:`ConditionDef` instances
with standard parameters, plus pre-built constants for the most common
configurations.

Usage::

    from respyra.configs.presets import slow_steady, PERTURBED_SLOW

    # Factory: customize parameters
    my_condition = slow_steady(freq_hz=0.15, n_cycles=4)

    # Constant: use standard defaults
    conditions = [PERTURBED_SLOW] * 6
"""

from __future__ import annotations

from respyra.core.target_generator import ConditionDef, SegmentDef

# ------------------------------------------------------------------ #
#  Factory functions                                                   #
# ------------------------------------------------------------------ #


def slow_steady(freq_hz: float = 0.1, n_cycles: int = 3) -> ConditionDef:
    """Slow, steady breathing at a single frequency.

    Parameters
    ----------
    freq_hz : float
        Breathing frequency in Hz (default 0.1 = one breath per 10 s).
    n_cycles : int
        Number of complete sinusoidal cycles per trial.
    """
    return ConditionDef("slow_steady", [SegmentDef(freq_hz, n_cycles)])


def perturbed_slow(
    freq_hz: float = 0.1,
    n_cycles: int = 3,
    feedback_gain: float = 1.5,
) -> ConditionDef:
    """Slow breathing with amplified visual feedback.

    The visual trace is multiplied by *feedback_gain* around the
    participant's breathing center, so the displayed signal appears
    larger (or smaller) than the actual breathing amplitude.

    Parameters
    ----------
    freq_hz : float
        Breathing frequency in Hz.
    n_cycles : int
        Number of complete cycles per trial.
    feedback_gain : float
        Multiplicative gain on the visual trace (1.0 = veridical).
    """
    return ConditionDef(
        "perturbed_slow",
        [SegmentDef(freq_hz, n_cycles)],
        feedback_gain=feedback_gain,
    )


def mixed_rhythm(
    freq_slow: float = 0.1,
    cycles_slow: int = 3,
    freq_fast: float = 0.3,
    cycles_fast: int = 1,
) -> ConditionDef:
    """Multi-segment rhythm with a slow phase followed by a fast phase.

    Parameters
    ----------
    freq_slow : float
        Frequency of the slow segment (Hz).
    cycles_slow : int
        Number of cycles in the slow segment.
    freq_fast : float
        Frequency of the fast segment (Hz).
    cycles_fast : int
        Number of cycles in the fast segment.
    """
    return ConditionDef(
        "mixed_rhythm",
        [SegmentDef(freq_slow, cycles_slow), SegmentDef(freq_fast, cycles_fast)],
    )


# ------------------------------------------------------------------ #
#  Standard instances                                                  #
# ------------------------------------------------------------------ #

SLOW_STEADY = slow_steady()
"""Slow steady breathing: 0.1 Hz, 3 cycles (30 s)."""

PERTURBED_SLOW = perturbed_slow()
"""Perturbed slow breathing: 0.1 Hz, 3 cycles, 1.5x feedback gain."""

MIXED_RHYTHM = mixed_rhythm()
"""Mixed rhythm: 3 cycles at 0.1 Hz + 1 cycle at 0.3 Hz (~33 s)."""
