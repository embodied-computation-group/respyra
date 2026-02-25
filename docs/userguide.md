# User Guide

This guide covers the full experiment workflow, configuration options, and data output format.

## Session flow

A full experiment session proceeds through the following stages:

### 1. Belt connection

The script connects to the Vernier Go Direct Respiration Belt via BLE (with automatic USB fallback). Connection happens **before** PsychoPy is imported to avoid a Windows COM threading conflict.

### 2. Participant info dialog

A PsychoPy dialog collects participant ID and session number. These are embedded in the output filename.

### 3. Range calibration (15 seconds)

The participant takes several comfortable deep breaths. The system records the breathing range and uses it to scale the target waveform to the participant's individual amplitude. Percentile-based outlier rejection (5th–95th percentile by default) excludes signal artefacts. A saturation warning is shown if force readings hit the sensor limits (0 N or 40 N).

![Range Calibration](../media/screenshots/01_range_calibration.png)

### 4. Trial loop

Each trial has three phases:

**Baseline** (10 s) — Breathe naturally. The system records the participant's resting breathing center for that trial.

![Baseline](../media/screenshots/02_baseline.png)

**Countdown** (3 s) — The target dot blends from the participant's current respiratory position into the sinusoidal target waveform. A large 3-2-1 counter is displayed.

![Countdown](../media/screenshots/03_countdown.png)

**Tracking** (30 s) — Follow the target dot with breathing. The dot changes color based on tracking error. The live breathing trace is shown scrolling from left to right.

![Tracking](../media/screenshots/04_tracking_veridical.png)

After each trial, a feedback screen displays the mean absolute tracking error.

### 5. Data output

Session data is saved incrementally to a CSV file in `data/`, with one row per sample. The filename encodes the participant ID, session, and timestamp (e.g., `sub-01_ses-001_2026-02-24_143022.csv`).

## Configuration

All experiment parameters are defined in `respyra/configs/breath_tracking.py`. Edit this file to customise the task.

### Belt settings

| Parameter | Default | Description |
|---|---|---|
| `CONNECTION` | `'ble'` | Connection type: `'ble'` or `'usb'` |
| `DEVICE_TO_OPEN` | `'proximity_pairing'` | BLE device selection strategy |
| `BELT_PERIOD_MS` | `100` | Sampling interval in ms (100 = 10 Hz) |
| `BELT_CHANNELS` | `[1]` | Sensor channels (1 = Force in Newtons) |

### Display settings

| Parameter | Default | Description |
|---|---|---|
| `FULLSCR` | `False` | Full-screen mode (set `True` for data collection) |
| `MONITOR_WIDTH_CM` | `53.0` | Physical screen width in cm |
| `MONITOR_DISTANCE_CM` | `57.0` | Viewing distance in cm |
| `MONITOR_SIZE_PIX` | `(1920, 1080)` | Screen resolution |
| `UNITS` | `'height'` | PsychoPy coordinate system |

### Phase timing

| Parameter | Default | Description |
|---|---|---|
| `RANGE_CAL_DURATION_SEC` | `15.0` | Range calibration duration (seconds) |
| `BASELINE_DURATION_SEC` | `10.0` | Baseline per trial (seconds) |
| `COUNTDOWN_DURATION_SEC` | `3.0` | Countdown per trial (seconds) |
| `TRACKING_DURATION_SEC` | `30.0` | Tracking per trial (seconds) |

### Trial structure

| Parameter | Default | Description |
|---|---|---|
| `CONDITIONS` | `[SLOW_STEADY, PERTURBED_SLOW]` | List of condition objects |
| `N_REPS` | `3` | Repetitions per condition |
| `TRIAL_METHOD` | `'sequential'` | `'sequential'` or `'random'` |

## Defining conditions

Conditions are built from composable segments using `SegmentDef` and `ConditionDef`:

```python
from respyra.core.target_generator import SegmentDef, ConditionDef

# 3 cycles at 0.1 Hz = 30 seconds of slow sinusoidal breathing
SLOW_STEADY = ConditionDef('slow_steady', [SegmentDef(0.1, 3)])

# Multi-frequency: 3 slow cycles + 1 fast cycle
MIXED_RHYTHM = ConditionDef('mixed_rhythm', [
    SegmentDef(0.1, 3),   # 30 s at 0.1 Hz
    SegmentDef(0.3, 1),   # 3.3 s at 0.3 Hz
])

# Same waveform as slow_steady but with amplified visual feedback
PERTURBED_SLOW = ConditionDef(
    'perturbed_slow',
    [SegmentDef(0.1, 3)],
    feedback_gain=1.5,  # trace is 1.5x amplified around center
)
```

Using integer cycle counts per segment ensures phase continuity at boundaries — the waveform loops seamlessly.

## Visual feedback modes

The target dot's color provides real-time tracking error feedback. Three modes are available (set via `DOT_FEEDBACK_MODE`):

**Graded** (default) — Continuous green → yellow → red color mapping using HSV interpolation. Error 0 = pure green; error ≥ `DOT_GRADED_MAX_ERROR_N` (3.0 N) = pure red.

**Binary** — Two-color threshold: yellow (good, error ≤ `ERROR_THRESHOLD_N`) or red (poor).

**Trinary** — Three-color: yellow (good, ≤ 1.0 N), orange (moderate, ≤ 2.0 N), red (poor, > 2.0 N).

## Visuomotor perturbation

The feedback gain parameter multiplies the **displayed** breathing trace around the participant's center:

```
f_display = center + gain × (f_actual − center)
```

- `gain = 1.0` — veridical feedback (what you breathe is what you see)
- `gain > 1.0` — amplified: small breathing excursions look larger on screen
- `gain < 1.0` — attenuated: large breathing excursions look smaller

The **target dot**, **tracking error computation**, and **color feedback** are always based on the true (unperturbed) signal — only the waveform trace is distorted. This creates a sensorimotor mismatch analogous to cursor rotation in visuomotor reaching studies.

## Data output format

The session CSV contains one row per sample with these columns:

| Column | Type | Description |
|---|---|---|
| `timestamp` | float | Time in seconds (from experiment clock, resets per phase) |
| `frame` | int | Frame counter |
| `force_n` | float | Force reading in Newtons from the respiration belt |
| `target_force` | float | Target force value (tracking phase only) |
| `error` | float | Signed error: target − actual (tracking phase only) |
| `phase` | str | `range_cal`, `baseline`, `countdown`, or `tracking` |
| `condition` | str | Condition name (e.g., `slow_steady`) |
| `trial_num` | int | Trial number (1-indexed) |
| `feedback_gain` | float | Active feedback gain for this trial |

## Post-session visualization

Generate a 6-panel summary figure:

```bash
respyra-plot data/sub-01_ses-001_2026-02-24.csv
```

The six panels show:
1. Full session force trace with target overlay and phase shading
2. Signed tracking error per trial
3. Per-trial mean absolute error (bar chart by condition)
4. Error distribution by condition (box plot with trial-level scatter)
5. Baseline calibration stability across trials (center ± amplitude)
6. Summary statistics (MAE, RMSE, per-condition breakdown)

Use `--no-show` to save the PNG without displaying interactively. Process multiple files with `respyra-plot data/*.csv --no-show`.
