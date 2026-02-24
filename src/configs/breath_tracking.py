"""Configuration for the respiratory motor control tracking task.

All experiment parameters live here so the script in
``src/scripts/breath_tracking_task.py`` contains no magic numbers.
"""

from src.core.target_generator import ConditionDef, SegmentDef

# ------------------------------------------------------------------ #
#  Belt connection                                                     #
# ------------------------------------------------------------------ #
CONNECTION = 'ble'                    # 'ble' or 'usb'
DEVICE_TO_OPEN = 'proximity_pairing'  # or specific name, e.g. 'GDX-RB 0K200101'
BELT_PERIOD_MS = 100                  # 10 Hz sampling
BELT_CHANNELS = [1]                   # Force only (channel 1)

# ------------------------------------------------------------------ #
#  Display                                                             #
# ------------------------------------------------------------------ #
FULLSCR = False                       # True for production
MONITOR_NAME = 'testMonitor'
MONITOR_WIDTH_CM = 53.0
MONITOR_DISTANCE_CM = 57.0
MONITOR_SIZE_PIX = (1920, 1080)
UNITS = 'height'                      # works without calibration
BG_COLOR = (-1, -1, -1)              # black

# ------------------------------------------------------------------ #
#  Waveform trace                                                      #
# ------------------------------------------------------------------ #
TRACE_RECT = (-0.6, -0.15, 0.55, 0.35)  # (left, bottom, right, top) in window units
TRACE_Y_RANGE = (0, 10)              # default force range; overridden dynamically after range cal
TRACE_COLOR = 'lime'
TRACE_DURATION_SEC = 5.0             # seconds of signal visible on screen
TRACE_BUFFER_SIZE = int(TRACE_DURATION_SEC * (1000 / BELT_PERIOD_MS))  # samples

# ------------------------------------------------------------------ #
#  Target dot                                                          #
# ------------------------------------------------------------------ #
DOT_RADIUS = 0.03                     # in window units (height)
DOT_X_OFFSET = 0.05                   # how far right of trace right edge
DOT_COLOR_GOOD = 'yellow'             # binary/trinary: good tracking color
DOT_COLOR_BAD = 'red'                 # binary/trinary: poor tracking color
DOT_COLOR_MID = 'orange'              # trinary only: moderate tracking color
ERROR_THRESHOLD_N = 1.0               # binary: good/bad cutoff (Newtons)
ERROR_THRESHOLD_MID_N = 2.0           # trinary: mid/bad cutoff (Newtons)

# Feedback mode: 'binary'  = good/bad (2 colors, 1 threshold)
#                'trinary' = good/mid/bad (3 colors, 2 thresholds)
#                'graded'  = continuous purple→green based on error
DOT_FEEDBACK_MODE = 'graded'
DOT_GRADED_MAX_ERROR_N = 3.0          # graded: error at which dot is fully purple

# ------------------------------------------------------------------ #
#  Trace border                                                        #
# ------------------------------------------------------------------ #
TRACE_BORDER_COLOR = '#333333'        # subtle border around trace area

# ------------------------------------------------------------------ #
#  Phase timing                                                        #
# ------------------------------------------------------------------ #
RANGE_CAL_DURATION_SEC = 15.0         # one-time max-range calibration at session start
RANGE_CAL_SCALE = 0.80                # fraction of max range used for target amplitude
RANGE_CAL_PERCENTILE_LO = 5           # lower percentile for outlier rejection (0-100)
RANGE_CAL_PERCENTILE_HI = 95          # upper percentile for outlier rejection (0-100)
FORCE_SATURATION_LO = 0.0             # sensor floor (GDX-RB range: 0-50 N)
FORCE_SATURATION_HI = 40.0            # sensor ceiling warning threshold
BASELINE_DURATION_SEC = 10.0          # breathe-naturally baseline (per trial)
COUNTDOWN_DURATION_SEC = 3.0          # 3..2..1 countdown before tracking
TRACKING_DURATION_SEC = 30.0          # active tracking phase

# ------------------------------------------------------------------ #
#  Conditions                                                          #
# ------------------------------------------------------------------ #
#   SLOW_STEADY: 3 cycles at 0.1 Hz = 30 s (matches tracking duration)
SLOW_STEADY = ConditionDef('slow_steady', [SegmentDef(0.1, 3)])

#   MIXED_RHYTHM: 3 cycles at 0.1 Hz + 1 cycle at 0.3 Hz = 33.33 s
MIXED_RHYTHM = ConditionDef('mixed_rhythm', [SegmentDef(0.1, 3), SegmentDef(0.3, 1)])

#   PERTURBED_SLOW: same as SLOW_STEADY but visual trace is amplified.
#   Participants must breathe with smaller amplitude to compensate.
PERTURBED_SLOW = ConditionDef('perturbed_slow', [SegmentDef(0.1, 3)], feedback_gain=1.5)

CONDITIONS = [SLOW_STEADY, PERTURBED_SLOW]

# ------------------------------------------------------------------ #
#  Trials                                                              #
# ------------------------------------------------------------------ #
N_REPS = 3                            # repetitions of each condition
TRIAL_METHOD = 'sequential'           # 'sequential' = alternating, 'random' = shuffled

# ------------------------------------------------------------------ #
#  Data output                                                         #
# ------------------------------------------------------------------ #
OUTPUT_DIR = 'data/'

DATA_COLUMNS = [
    'timestamp',
    'frame',
    'force_n',
    'target_force',
    'error',
    'phase',
    'condition',
    'trial_num',
    'feedback_gain',
]

# ------------------------------------------------------------------ #
#  Input                                                               #
# ------------------------------------------------------------------ #
ESCAPE_KEY = 'escape'
