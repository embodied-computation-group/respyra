"""Demo configuration: 5 slow-and-steady breathing trials.

A lightweight config for quick demonstrations and testing.
All trials use the slow_steady condition (0.1 Hz, 4 cycles = 40 s).
No counterbalancing, no perturbed condition.
"""

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
from respyra.core.target_generator import ConditionDef, SegmentDef

# ------------------------------------------------------------------ #
#  Display                                                             #
# ------------------------------------------------------------------ #
FULLSCR = False
MONITOR_SIZE_PIX = (1920, 1080)

# ------------------------------------------------------------------ #
#  Condition — slow and steady (4 cycles at 0.1 Hz = 40 s)           #
# ------------------------------------------------------------------ #
SLOW_STEADY = ConditionDef("slow_steady", [SegmentDef(0.1, 4)])

# ------------------------------------------------------------------ #
#  Tracking duration — matches 4 cycles at 0.1 Hz                    #
# ------------------------------------------------------------------ #
TRACKING_DURATION_SEC = 40.0

# ------------------------------------------------------------------ #
#  Trials — 5 identical slow_steady trials                            #
# ------------------------------------------------------------------ #
N_REPS = 1
TRIAL_METHOD = "sequential"

# ------------------------------------------------------------------ #
#  Data output                                                         #
# ------------------------------------------------------------------ #
OUTPUT_DIR = "data/"


def build_conditions(session_num: int | str) -> list[ConditionDef]:
    """Return 5 slow_steady trials (session number is ignored)."""
    return [SLOW_STEADY] * 5


CONDITIONS = build_conditions(1)

# ------------------------------------------------------------------ #
#  Structured config (for use with respyra.core.runner)                #
# ------------------------------------------------------------------ #
from dataclasses import replace as _replace  # noqa: E402

from respyra.configs.breath_tracking import CONFIG as _BASE  # noqa: E402
from respyra.configs.experiment_config import TrialConfig as _TrialConfig  # noqa: E402

CONFIG = _replace(
    _BASE,
    name="Breath Tracking Demo (5 trials)",
    timing=_replace(_BASE.timing, tracking_duration_sec=TRACKING_DURATION_SEC),
    trial=_TrialConfig(
        conditions=CONDITIONS,
        n_reps=N_REPS,
        method=TRIAL_METHOD,
        build_conditions=build_conditions,
    ),
)
