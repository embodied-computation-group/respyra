"""Demo: 5 slow-and-steady breathing trials.

A lightweight config for quick demonstrations and testing.
All trials use slow_steady at 0.1 Hz, 4 cycles (40 s each).
No counterbalancing, no perturbed condition, windowed mode.
"""

from dataclasses import replace

from defaults import CONFIG as _BASE

from respyra.configs.experiment_config import TrialConfig
from respyra.configs.presets import slow_steady

SLOW_4 = slow_steady(n_cycles=4)

CONFIG = replace(
    _BASE,
    name="Breath Tracking Demo (5 trials)",
    timing=replace(_BASE.timing, tracking_duration_sec=40.0),
    trial=TrialConfig(
        conditions=[SLOW_4] * 5,
        n_reps=1,
        method="sequential",
    ),
)
