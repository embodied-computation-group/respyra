#!/usr/bin/env python3
"""Generate screenshots of each task phase for documentation.

Renders each key visual state of the breath tracking task using real
session data (no belt required) and saves PNGs to media/screenshots/.

Usage
-----
    python -m src.scripts.generate_screenshots
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from psychopy import core, visual

from src.configs.breath_tracking import (
    BG_COLOR,
    DOT_GRADED_MAX_ERROR_N,
    DOT_RADIUS,
    DOT_X_OFFSET,
    MONITOR_DISTANCE_CM,
    MONITOR_NAME,
    MONITOR_SIZE_PIX,
    MONITOR_WIDTH_CM,
    TRACE_BORDER_COLOR,
    TRACE_COLOR,
    TRACE_RECT,
    TRACE_Y_RANGE,
    UNITS,
)
from src.core.display import SignalTrace, create_monitor, create_window
from src.scripts.breath_tracking_task import _graded_dot_color


# ------------------------------------------------------------------ #
#  Real session data (from sub-micah_ses-001_2026-02-24_205556.csv)   #
# ------------------------------------------------------------------ #
# Each buffer is 50 samples = 5 seconds at 10 Hz, extracted from
# representative windows of an actual experimental session.

# Range calibration: deep breaths, one full inhalation-exhalation cycle
RANGE_CAL_FORCES = [
    0.59, 0.52, 0.47, 0.46, 0.47, 0.52, 0.61, 0.71, 0.83, 0.95,
    1.08, 1.20, 1.30, 1.40, 1.51, 1.60, 1.68, 1.77, 1.85, 1.94,
    2.02, 2.11, 2.17, 2.22, 2.30, 2.37, 2.44, 2.51, 2.56, 2.59,
    2.63, 2.69, 2.75, 2.78, 2.79, 2.75, 2.72, 2.69, 2.63, 2.52,
    2.37, 2.19, 2.00, 1.80, 1.62, 1.47, 1.33, 1.20, 1.06, 0.91,
]

# Baseline: natural quiet breathing (~0.25 Hz), 2-3 visible breaths
BASELINE_FORCES = [
    0.89, 0.96, 1.04, 1.11, 1.17, 1.20, 1.18, 1.11, 1.04, 0.97,
    0.88, 0.81, 0.72, 0.63, 0.54, 0.46, 0.41, 0.38, 0.38, 0.43,
    0.52, 0.59, 0.67, 0.76, 0.84, 0.91, 0.99, 1.05, 1.12, 1.17,
    1.24, 1.30, 1.32, 1.30, 1.24, 1.16, 1.05, 0.97, 0.90, 0.84,
    0.77, 0.72, 0.65, 0.56, 0.48, 0.43, 0.41, 0.44, 0.52, 0.60,
]

# Tracking veridical (trial 1, t=10-15s): participant following 0.1 Hz target
TRACKING_FORCES = [
    1.27, 1.33, 1.40, 1.48, 1.57, 1.65, 1.72, 1.78, 1.83, 1.92,
    2.01, 2.09, 2.15, 2.21, 2.25, 2.29, 2.36, 2.42, 2.48, 2.54,
    2.59, 2.61, 2.64, 2.67, 2.70, 2.71, 2.70, 2.67, 2.64, 2.63,
    2.63, 2.60, 2.57, 2.53, 2.49, 2.42, 2.35, 2.31, 2.28, 2.24,
    2.20, 2.17, 2.10, 2.02, 1.92, 1.84, 1.77, 1.68, 1.59, 1.52,
]
TRACKING_TARGETS = [
    1.45, 1.52, 1.60, 1.66, 1.72, 1.79, 1.85, 1.92, 1.97, 2.03,
    2.09, 2.14, 2.19, 2.23, 2.27, 2.32, 2.36, 2.39, 2.42, 2.45,
    2.47, 2.49, 2.50, 2.51, 2.52, 2.52, 2.52, 2.51, 2.50, 2.48,
    2.46, 2.44, 2.41, 2.38, 2.35, 2.31, 2.27, 2.22, 2.17, 2.12,
    2.06, 2.01, 1.95, 1.90, 1.84, 1.77, 1.71, 1.64, 1.57, 1.51,
]

# Bad tracking (trial 4, t=20.8-25.7s): participant oscillating faster than
# target, large divergence.  ~2.5 visible breath cycles + high error.
BAD_TRACKING_FORCES = [
    1.82, 1.91, 1.98, 2.03, 2.06, 2.08, 2.10, 2.15, 2.20, 2.26,
    2.29, 2.33, 2.34, 2.31, 2.31, 2.30, 2.26, 2.19, 2.13, 2.06,
    1.98, 1.91, 1.85, 1.78, 1.73, 1.74, 1.78, 1.82, 1.89, 1.94,
    1.94, 1.92, 1.86, 1.79, 1.72, 1.68, 1.68, 1.72, 1.77, 1.79,
    1.75, 1.70, 1.64, 1.62, 1.61, 1.58, 1.56, 1.55, 1.54, 1.51,
]
BAD_TRACKING_TARGETS = [
    2.01, 2.08, 2.12, 2.18, 2.22, 2.27, 2.31, 2.35, 2.38, 2.42,
    2.44, 2.46, 2.48, 2.50, 2.51, 2.52, 2.52, 2.52, 2.51, 2.50,
    2.49, 2.47, 2.45, 2.42, 2.39, 2.36, 2.32, 2.28, 2.24, 2.19,
    2.14, 2.08, 2.03, 1.97, 1.91, 1.85, 1.78, 1.72, 1.65, 1.58,
    1.52, 1.46, 1.39, 1.33, 1.26, 1.19, 1.13, 1.06, 1.00, 0.94,
]

# Calibration values (from the same session, P5/P95 clipped)
RANGE_CENTER = 1.45
Y_MIN = -0.44
Y_MAX = 3.33


# ------------------------------------------------------------------ #

def _position_dot(
    target_force: float,
    y_min: float,
    y_max: float,
    trace_bottom: float,
    trace_top: float,
    trace_right: float,
) -> tuple[float, float]:
    """Compute dot screen position from a target force value."""
    y_span = y_max - y_min
    if y_span == 0:
        normed = 0.5
    else:
        normed = (target_force - y_min) / y_span
        normed = float(np.clip(normed, 0.0, 1.0))
    dot_y = trace_bottom + normed * (trace_top - trace_bottom)
    return (trace_right + DOT_X_OFFSET, dot_y)


def _capture(win, path: str) -> None:
    """Flip, capture, and save a screenshot."""
    win.flip()
    win.getMovieFrame()
    win.saveMovieFrames(path)
    print(f'Saved: {path}')


def main():
    out_dir = Path('media/screenshots')
    out_dir.mkdir(parents=True, exist_ok=True)

    # -- Window & stimuli (mirrors breath_tracking_task.py) ----------------
    monitor = create_monitor(
        MONITOR_NAME, MONITOR_WIDTH_CM, MONITOR_DISTANCE_CM, MONITOR_SIZE_PIX,
    )
    win = create_window(
        fullscr=False,
        monitor=monitor,
        units=UNITS,
        color=BG_COLOR,
        size=MONITOR_SIZE_PIX,
    )

    trace_left, trace_bottom, trace_right, trace_top = TRACE_RECT
    trace_center_y = (trace_bottom + trace_top) / 2

    trace = SignalTrace(
        win,
        trace_rect=TRACE_RECT,
        y_range=TRACE_Y_RANGE,
        color=TRACE_COLOR,
    )

    trace_border = visual.Rect(
        win,
        width=trace_right - trace_left,
        height=trace_top - trace_bottom,
        pos=((trace_left + trace_right) / 2, (trace_bottom + trace_top) / 2),
        lineColor=TRACE_BORDER_COLOR,
        lineWidth=1.0,
        fillColor=None,
    )

    phase_title = visual.TextStim(
        win, text='', color='#aaaaaa', height=0.05,
        pos=(0.0, 0.45), bold=True,
    )

    status_text = visual.TextStim(
        win, text='', color='white', height=0.03,
        pos=(0.0, trace_bottom - 0.06), wrapWidth=1.5,
    )

    countdown_text = visual.TextStim(
        win, text='', color='white', height=0.15,
        pos=(0.0, trace_center_y),
    )

    target_dot = visual.Circle(
        win, radius=DOT_RADIUS,
        fillColor='yellow', lineColor='yellow',
    )

    # Set y-range from real calibration
    trace.y_min = Y_MIN
    trace.y_max = Y_MAX

    try:
        # ==============================================================
        # 1. Range Calibration
        # ==============================================================
        phase_title.text = "RANGE CALIBRATION"
        status_text.text = "Comfortable deep breaths -- 8s remaining"

        trace_border.draw()
        trace.draw(RANGE_CAL_FORCES)
        phase_title.draw()
        status_text.draw()
        _capture(win, str(out_dir / '01_range_calibration.png'))

        # ==============================================================
        # 2. Baseline
        # ==============================================================
        phase_title.text = "BASELINE -- Trial 1/6"
        status_text.text = "Breathe naturally -- 5s remaining"

        trace_border.draw()
        trace.draw(BASELINE_FORCES)
        phase_title.draw()
        status_text.draw()
        _capture(win, str(out_dir / '02_baseline.png'))

        # ==============================================================
        # 3. Countdown
        # ==============================================================
        phase_title.text = "GET READY -- Trial 1/6"
        status_text.text = "Get ready -- follow the dot!"
        countdown_text.text = "2"

        # Dot: gray (neutral), positioned at current target
        target_force = TRACKING_TARGETS[len(TRACKING_TARGETS) // 2]
        target_dot.fillColor = '#aaaaaa'
        target_dot.lineColor = '#aaaaaa'
        target_dot.pos = _position_dot(
            target_force, Y_MIN, Y_MAX, trace_bottom, trace_top, trace_right,
        )

        # Show baseline breathing transitioning toward tracking
        trace_border.draw()
        trace.draw(BASELINE_FORCES)
        target_dot.draw()
        countdown_text.draw()
        phase_title.draw()
        status_text.draw()
        _capture(win, str(out_dir / '03_countdown.png'))

        countdown_text.text = ''

        # ==============================================================
        # 4. Tracking -- Veridical (gain = 1.0)
        # ==============================================================
        phase_title.text = "TRACKING -- Trial 1/6"
        status_text.text = "Follow the dot -- 15s remaining"

        # Dot: colored by graded error (low error → green)
        target_force = TRACKING_TARGETS[-1]
        current_force = TRACKING_FORCES[-1]
        error = abs(target_force - current_force)
        color = _graded_dot_color(error, DOT_GRADED_MAX_ERROR_N)
        target_dot.fillColor = color
        target_dot.lineColor = color
        target_dot.pos = _position_dot(
            target_force, Y_MIN, Y_MAX, trace_bottom, trace_top, trace_right,
        )

        trace_border.draw()
        trace.draw(TRACKING_FORCES)
        target_dot.draw()
        phase_title.draw()
        status_text.draw()
        _capture(win, str(out_dir / '04_tracking_veridical.png'))

        # ==============================================================
        # 5. Tracking -- Bad (high error, red/orange dot)
        # ==============================================================
        phase_title.text = "TRACKING -- Trial 4/6"
        status_text.text = "Follow the dot -- 5s remaining"

        # Dot: colored by graded error (high error → red/orange)
        target_force = BAD_TRACKING_TARGETS[-1]
        current_force = BAD_TRACKING_FORCES[-1]
        error = abs(target_force - current_force)
        color = _graded_dot_color(error, DOT_GRADED_MAX_ERROR_N)
        target_dot.fillColor = color
        target_dot.lineColor = color
        target_dot.pos = _position_dot(
            target_force, Y_MIN, Y_MAX, trace_bottom, trace_top, trace_right,
        )

        trace_border.draw()
        trace.draw(BAD_TRACKING_FORCES)
        target_dot.draw()
        phase_title.draw()
        status_text.draw()
        _capture(win, str(out_dir / '05_tracking_bad.png'))

        print(f'\nAll screenshots saved to {out_dir}/')

    finally:
        win.close()
        core.quit()


if __name__ == '__main__':
    main()
