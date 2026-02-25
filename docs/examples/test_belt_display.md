# Test: Belt + Display Integration

**Script:** `respyra/scripts/test_belt_display.py`

**What it demonstrates:** A simpler integration test that connects the belt and displays the live breathing waveform with button-press event logging.

## How to run

```bash
python -m respyra.scripts.test_belt_display
```

## What it does

1. **Connects to the belt** (BLE with USB fallback, before PsychoPy import).
2. **Shows instructions** and waits for SPACE to begin.
3. **Displays the live breathing trace** in real time.
4. **Records button presses** — pressing SPACE logs a keypress event with a red marker flash.
5. **Saves data** as an incremental CSV with force samples and keypress events interleaved.

## How it differs from the full experiment

| Feature | test_belt_display | breath_tracking_task |
|---|---|---|
| Target dot | No | Yes |
| Conditions | None | Configurable |
| Calibration | No | Range + baseline |
| Trial structure | Free-running | Baseline → countdown → tracking |
| Feedback | None | Color-coded error |

This script is useful for:
- Verifying belt connectivity and data quality before running a full session
- Observing the raw breathing signal without experiment structure
- Testing button-press event timing
