"""Configuration for the test belt display experiment."""

# --- Connection ---
CONNECTION = "ble"  # 'ble' or 'usb'
DEVICE_TO_OPEN = "proximity_pairing"  # or specific device name, e.g. 'GDX-RB 081000A1'
BELT_PERIOD_MS = 100  # 10 Hz sampling
BELT_CHANNELS = [1]  # Force only (channel 1)

# --- Display ---
FULLSCR = False  # True for production
MONITOR_NAME = "testMonitor"
MONITOR_WIDTH_CM = 53.0
MONITOR_DISTANCE_CM = 57.0
MONITOR_SIZE_PIX = (1920, 1080)
UNITS = "height"  # works without calibration
BG_COLOR = (-1, -1, -1)  # black

# --- Waveform trace ---
TRACE_RECT = (-0.8, -0.3, 0.8, 0.3)  # (left, bottom, right, top) in window units
TRACE_Y_RANGE = (0, 50)  # force range in Newtons
TRACE_COLOR = "lime"
TRACE_DURATION_SEC = 5.0  # seconds of signal visible on screen
TRACE_BUFFER_SIZE = int(TRACE_DURATION_SEC * (1000 / BELT_PERIOD_MS))  # samples to display

# --- Task ---
RECORD_DURATION_SEC = 60  # total recording time (0 = unlimited, escape to quit)
RESPONSE_KEYS = ["space"]  # button press to record
ESCAPE_KEY = "escape"

# --- Data output ---
OUTPUT_DIR = "data/"
