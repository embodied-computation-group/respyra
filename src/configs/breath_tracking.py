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
TRACE_RECT = (-0.6, -0.3, 0.55, 0.3)  # (left, bottom, right, top) in window units
TRACE_Y_RANGE = (0, 15)              # force range in Newtons (narrower than test_experiment)
TRACE_COLOR = 'lime'
TRACE_DURATION_SEC = 5.0             # seconds of signal visible on screen
TRACE_BUFFER_SIZE = int(TRACE_DURATION_SEC * (1000 / BELT_PERIOD_MS))  # samples

# ------------------------------------------------------------------ #
#  Target dot                                                          #
# ------------------------------------------------------------------ #
DOT_RADIUS = 0.03                     # in window units (height)
DOT_X_OFFSET = 0.05                   # how far right of trace right edge
DOT_COLOR_GOOD = 'yellow'             # when tracking error <= threshold
DOT_COLOR_BAD = 'red'                 # when tracking error > threshold
ERROR_THRESHOLD_N = 1.0               # acceptable error band in Newtons

# ------------------------------------------------------------------ #
#  Phase timing                                                        #
# ------------------------------------------------------------------ #
BASELINE_DURATION_SEC = 10.0          # breathe-naturally baseline
COUNTDOWN_DURATION_SEC = 3.0          # 3..2..1 countdown before tracking
TRACKING_DURATION_SEC = 30.0          # active tracking phase

# ------------------------------------------------------------------ #
#  Conditions                                                          #
# ------------------------------------------------------------------ #
#   SLOW_STEADY: 3 cycles at 0.1 Hz = 30 s (matches tracking duration)
SLOW_STEADY = ConditionDef('slow_steady', [SegmentDef(0.1, 3)])

#   MIXED_RHYTHM: 3 cycles at 0.1 Hz + 1 cycle at 0.3 Hz = 33.33 s
MIXED_RHYTHM = ConditionDef('mixed_rhythm', [SegmentDef(0.1, 3), SegmentDef(0.3, 1)])

CONDITIONS = [SLOW_STEADY, MIXED_RHYTHM]

# ------------------------------------------------------------------ #
#  Trials                                                              #
# ------------------------------------------------------------------ #
N_REPS = 3                            # repetitions of each condition

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
]

# ------------------------------------------------------------------ #
#  Input                                                               #
# ------------------------------------------------------------------ #
ESCAPE_KEY = 'escape'
