"""Configuration for the validation study (4 sessions, 12 trials each).

Extends the base breath_tracking config with:
- 4 breath cycles per trial (40 s at 0.1 Hz)
- 12 trials per session (6 slow_steady + 6 perturbed_slow)
- Counterbalanced starting condition across sessions (ABAB/BABA)

To use: change the import in breath_tracking_task.py from
    from respyra.configs.breath_tracking import ...
to
    from respyra.configs.validation_study import ...

The session number entered in the participant dialog determines
counterbalancing: odd sessions start slow_steady, even start perturbed.
"""

from respyra.core.target_generator import ConditionDef, SegmentDef

# ------------------------------------------------------------------ #
#  Inherit all defaults from the base config                          #
# ------------------------------------------------------------------ #
from respyra.configs.breath_tracking import (  # noqa: F401, E402
    BASELINE_DURATION_SEC,
    BELT_CHANNELS,
    BELT_PERIOD_MS,
    BG_COLOR,
    CONNECTION,
    COUNTDOWN_DURATION_SEC,
    DATA_COLUMNS,
    DEVICE_TO_OPEN,
    DOT_COLOR_BAD,
    DOT_COLOR_GOOD,
    DOT_COLOR_MID,
    DOT_FEEDBACK_MODE,
    DOT_GRADED_MAX_ERROR_N,
    DOT_RADIUS,
    DOT_X_OFFSET,
    ERROR_THRESHOLD_MID_N,
    ERROR_THRESHOLD_N,
    ESCAPE_KEY,
    FORCE_SATURATION_HI,
    FORCE_SATURATION_LO,
    MONITOR_DISTANCE_CM,
    MONITOR_NAME,
    MONITOR_WIDTH_CM,
    RANGE_CAL_DURATION_SEC,
    RANGE_CAL_PERCENTILE_HI,
    RANGE_CAL_PERCENTILE_LO,
    RANGE_CAL_SCALE,
    TRACE_BORDER_COLOR,
    TRACE_BUFFER_SIZE,
    TRACE_COLOR,
    TRACE_RECT,
    TRACE_Y_RANGE,
    UNITS,
)

# ------------------------------------------------------------------ #
#  Display override                                                    #
# ------------------------------------------------------------------ #
FULLSCR = True
MONITOR_SIZE_PIX = (3440, 1440)

# ------------------------------------------------------------------ #
#  Conditions — 4 cycles per trial (40 s at 0.1 Hz)                  #
# ------------------------------------------------------------------ #
SLOW_STEADY = ConditionDef("slow_steady", [SegmentDef(0.1, 4)])
PERTURBED_SLOW = ConditionDef("perturbed_slow", [SegmentDef(0.1, 4)], feedback_gain=2.0)

# ------------------------------------------------------------------ #
#  Block size                                                          #
# ------------------------------------------------------------------ #
BLOCK_SIZE = 6

# ------------------------------------------------------------------ #
#  Trials                                                              #
# ------------------------------------------------------------------ #
N_REPS = 1  # trial list is fully expanded by build_conditions()
TRIAL_METHOD = "sequential"

# ------------------------------------------------------------------ #
#  Tracking duration — matches 4 cycles at 0.1 Hz                    #
# ------------------------------------------------------------------ #
TRACKING_DURATION_SEC = 40.0

# ------------------------------------------------------------------ #
#  Data output                                                         #
# ------------------------------------------------------------------ #
OUTPUT_DIR = "data/"


def build_conditions(session_num: int) -> list[ConditionDef]:
    """Build the blocked trial list based on session number.

    Odd sessions (1, 3): slow_steady block first.
    Even sessions (2, 4): perturbed block first.
    """
    if int(session_num) % 2 == 1:
        return [SLOW_STEADY] * BLOCK_SIZE + [PERTURBED_SLOW] * BLOCK_SIZE
    else:
        return [PERTURBED_SLOW] * BLOCK_SIZE + [SLOW_STEADY] * BLOCK_SIZE


# Default CONDITIONS for backward compatibility — overridden by the
# runner after the participant dialog.
CONDITIONS = build_conditions(1)
