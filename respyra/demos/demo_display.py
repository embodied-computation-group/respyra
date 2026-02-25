#!/usr/bin/env python3
"""Demo: PsychoPy waveform display with fake sinusoidal data.

No hardware required.  Generates a synthetic breathing signal and renders
it with draw_signal_trace().  Press SPACE to print a marker to the
console.  Press ESCAPE to quit.

Run from the project root:
    python -m respyra.demos.demo_display
"""

import math
from collections import deque

from psychopy import core

from respyra.core.display import create_window, draw_signal_trace
from respyra.core.events import check_keys

# -- Parameters --
BUFFER_SIZE = 50  # rolling buffer length (number of points on screen)
FAKE_AMPLITUDE = 10.0  # peak-to-peak of fake signal (Newtons)
FAKE_BASELINE = 15.0  # centre of oscillation
FAKE_FREQ = 0.25  # Hz -- roughly 15 breaths per minute
Y_RANGE = (0, 50)  # expected data range for scaling


def main():
    win = create_window(fullscr=False)
    exp_clock = core.Clock()

    # Pre-create instruction text outside the loop (following conventions)
    from psychopy import visual

    instruction = visual.TextStim(
        win,
        text=("Fake waveform demo.\n\nPress SPACE to place a marker.\nPress ESCAPE to quit."),
        color="white",
        height=0.04,
        wrapWidth=1.5,
    )

    # Show instructions -- wait for space or escape
    from psychopy import event as _evt

    _evt.clearEvents()
    instruction.draw()
    win.flip()
    _evt.waitKeys(keyList=["space", "escape"])

    # Rolling buffer for the waveform
    buffer = deque(maxlen=BUFFER_SIZE)
    counter = 0

    try:
        while True:
            # Generate one new fake data point per frame
            t = exp_clock.getTime()
            value = FAKE_BASELINE + FAKE_AMPLITUDE * math.sin(2.0 * math.pi * FAKE_FREQ * t)
            buffer.append(value)
            counter += 1

            # Draw the waveform
            draw_signal_trace(win, list(buffer), y_range=Y_RANGE)

            # Check for keypresses (non-blocking)
            keys = check_keys(["space", "escape"], clock=exp_clock)
            for key, timestamp in keys:
                if key == "escape":
                    print("Escape pressed -- quitting.")
                    core.quit()
                if key == "space":
                    print(f"MARKER at t={timestamp:.3f}s  (frame {counter})")

            win.flip()

    finally:
        win.close()
        core.quit()


if __name__ == "__main__":
    main()
