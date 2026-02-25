# Demo: PsychoPy Display

**Script:** `respyra/demos/demo_display.py`

**What it demonstrates:** Real-time waveform rendering with PsychoPy using synthetic data (no hardware required).

## How to run

```bash
python -m respyra.demos.demo_display
```

## What it does

1. **Creates a PsychoPy window** using `create_window()` with project defaults (black background, height units).
2. **Generates a synthetic sinusoidal signal** (0.25 Hz, 15 N baseline, 10 N amplitude) to simulate breathing.
3. **Renders the waveform** using `draw_signal_trace()`, which internally caches a `SignalTrace` object per window.
4. **Handles input** — SPACE prints a marker to the console, ESCAPE quits.

## Key code patterns

### Using `draw_signal_trace()` (convenience function)

```python
from respyra.core.display import create_window, draw_signal_trace

win = create_window(fullscr=False)
buffer = deque(maxlen=50)

while True:
    buffer.append(new_value)
    draw_signal_trace(win, list(buffer), y_range=(0, 50))
    win.flip()
```

The convenience function caches the `SignalTrace` internally — safe to call every frame without allocations.

### Non-blocking key checks

```python
from respyra.core.events import check_keys

keys = check_keys(['space', 'escape'], clock=exp_clock)
for key, timestamp in keys:
    if key == 'escape':
        core.quit()
```

## Expected output

A PsychoPy window with a scrolling green sinusoidal trace on a black background. The waveform updates every frame (~60 Hz).
