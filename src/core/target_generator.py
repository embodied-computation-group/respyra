"""Target waveform generator for respiratory motor control tracking.

Generates sinusoidal breathing-target waveforms from a sequence of
frequency/cycle segments.  After a baseline calibration phase the generator
maps target values into the participant's actual force range so the target
dot stays within their comfortable breathing amplitude.

Usage
-----
    from src.core.target_generator import (
        SegmentDef, ConditionDef, TargetGenerator, calibrate_from_baseline,
    )

    center, amplitude = calibrate_from_baseline(baseline_forces)
    condition = ConditionDef('slow_steady', [SegmentDef(0.1, 3)])
    gen = TargetGenerator(condition, center, amplitude)

    target_force = gen.get_target(t)  # call each frame with tracking time
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence


# ------------------------------------------------------------------ #
#  Data definitions                                                    #
# ------------------------------------------------------------------ #

@dataclass
class SegmentDef:
    """One constant-frequency segment of a breathing-target pattern.

    Parameters
    ----------
    freq_hz : float
        Target breathing frequency in Hz (e.g. 0.1 = one breath per 10 s).
    n_cycles : int
        Number of complete sinusoidal cycles.  Using integer cycles
        guarantees phase continuity at segment boundaries.
    """

    freq_hz: float
    n_cycles: int

    @property
    def duration(self) -> float:
        """Segment duration in seconds (n_cycles / freq_hz)."""
        return self.n_cycles / self.freq_hz


@dataclass
class ConditionDef:
    """A named experimental condition composed of one or more segments.

    Parameters
    ----------
    name : str
        Human-readable label used in data files (e.g. ``'slow_steady'``).
    segments : list[SegmentDef]
        Ordered list of segments that form the repeating pattern.
    feedback_gain : float
        Multiplicative gain applied to the visual trace around the
        participant's breathing center.  ``1.0`` = veridical feedback.
        Values > 1 amplify displayed deviations; < 1 attenuate them.
    """

    name: str
    segments: list[SegmentDef] = field(default_factory=list)
    feedback_gain: float = 1.0

    @property
    def total_duration(self) -> float:
        """Total duration of one pass through all segments (seconds)."""
        return sum(seg.duration for seg in self.segments)


# ------------------------------------------------------------------ #
#  Baseline calibration                                                #
# ------------------------------------------------------------------ #

def calibrate_from_baseline(
    force_samples: Sequence[float],
    min_amplitude: float = 0.5,
) -> tuple[float, float]:
    """Derive target center and amplitude from baseline breathing data.

    Parameters
    ----------
    force_samples : sequence of float
        Raw force readings (in Newtons) collected during baseline.
    min_amplitude : float
        Floor for the half-amplitude to prevent degenerate targets when
        baseline variance is very low.

    Returns
    -------
    center : float
        Midpoint of the participant's breathing range, used as the DC
        offset for the sinusoidal target.
    amplitude : float
        Half-amplitude of the sinusoidal target, clamped to at least
        *min_amplitude*.
    """
    if not force_samples:
        # Fallback when no data is available (e.g. belt disconnected).
        return 5.0, 2.0

    lo = min(force_samples)
    hi = max(force_samples)
    center = (hi + lo) / 2.0
    amplitude = max((hi - lo) / 2.0, min_amplitude)
    return center, amplitude


# ------------------------------------------------------------------ #
#  Target generator                                                    #
# ------------------------------------------------------------------ #

class TargetGenerator:
    """Real-time sinusoidal breathing-target generator.

    Call :meth:`get_target` each frame with the current tracking time
    to obtain the target force value for the respiratory tracking dot.

    The waveform is ``center + amplitude * sin(2 * pi * freq * t_local)``
    where *t_local* is the time within the currently active segment.
    Multi-segment patterns loop seamlessly because each segment uses
    an integer number of cycles (phase-continuous boundaries).

    Parameters
    ----------
    condition : ConditionDef
        Defines the segment sequence.
    center : float
        DC offset (Newtons), typically from :func:`calibrate_from_baseline`.
    amplitude : float
        Half-amplitude (Newtons) of the sinusoidal target.
    """

    def __init__(
        self,
        condition: ConditionDef,
        center: float,
        amplitude: float,
    ) -> None:
        self.condition = condition
        self.center = center
        self.amplitude = amplitude
        self._total_duration = condition.total_duration

    def get_target(self, t: float) -> float:
        """Return the target force value at time *t* (seconds).

        Time is wrapped modulo the total pattern duration so the
        waveform repeats indefinitely.

        Parameters
        ----------
        t : float
            Elapsed time in seconds since the tracking phase began.

        Returns
        -------
        float
            Target force in Newtons.
        """
        # Wrap time into the repeating pattern
        t_wrapped = t % self._total_duration

        # Walk segments to find the active one
        elapsed_in_segments = 0.0
        for seg in self.condition.segments:
            seg_end = elapsed_in_segments + seg.duration
            if t_wrapped < seg_end:
                t_local = t_wrapped - elapsed_in_segments
                return self.center + self.amplitude * math.sin(
                    2.0 * math.pi * seg.freq_hz * t_local
                )
            elapsed_in_segments = seg_end

        # Floating-point edge case: t_wrapped exactly equals total_duration.
        # Fall back to the last segment's endpoint (sin at full cycle = 0).
        return self.center
