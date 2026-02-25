"""Validation study: 4 sessions, 12 trials each, counterbalanced.

- 4 breath cycles per trial (40 s at 0.1 Hz)
- 12 trials per session (6 slow_steady + 6 perturbed_slow)
- Counterbalanced starting condition across sessions (ABAB/BABA)
- Perturbed condition uses 2.0x feedback gain

The session number entered in the participant dialog determines
counterbalancing: odd sessions start slow_steady, even start perturbed.
"""

from dataclasses import replace

from defaults import CONFIG as _BASE

from respyra.configs.experiment_config import TrialConfig
from respyra.configs.presets import perturbed_slow, slow_steady

SLOW_4 = slow_steady(n_cycles=4)
PERTURBED_4 = perturbed_slow(n_cycles=4, feedback_gain=2.0)
BLOCK_SIZE = 6


def build_conditions(session_num):
    """Build counterbalanced trial list based on session number.

    Odd sessions (1, 3): slow_steady block first.
    Even sessions (2, 4): perturbed block first.
    """
    if int(session_num) % 2 == 1:
        return [SLOW_4] * BLOCK_SIZE + [PERTURBED_4] * BLOCK_SIZE
    else:
        return [PERTURBED_4] * BLOCK_SIZE + [SLOW_4] * BLOCK_SIZE


CONFIG = replace(
    _BASE,
    name="Validation Study",
    display=replace(_BASE.display, fullscr=True, monitor_size_pix=(3440, 1440)),
    timing=replace(_BASE.timing, tracking_duration_sec=40.0),
    trial=TrialConfig(
        conditions=build_conditions(1),
        n_reps=1,
        method="sequential",
        build_conditions=build_conditions,
    ),
)
