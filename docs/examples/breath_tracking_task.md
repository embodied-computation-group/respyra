# Full Experiment: Breath Tracking Task

**Script:** `respyra/scripts/breath_tracking_task.py`

**What it demonstrates:** The complete respiratory tracking experiment with calibration, multi-condition trials, and data logging.

## How to run

```bash
respyra-task
# or:
python -m respyra.scripts.breath_tracking_task
```

## Architecture overview

The script follows this sequence:

1. **Belt connection** — connects before PsychoPy import (Windows BLE requirement)
2. **PsychoPy setup** — participant dialog, monitor profile, window, pre-created stimuli
3. **Range calibration** — 15 s of deep breaths to establish breathing range
4. **Trial loop** — for each condition × N reps:
   - Baseline (10 s) → Countdown (3 s) → Tracking (30 s) → Feedback
5. **Cleanup** — belt stop, file close, window close (in `finally` block)

## Key code patterns

### Belt-before-PsychoPy import order

```python
def run_experiment():
    # 1. Connect belt BEFORE importing PsychoPy
    belt = _connect_belt()

    # 2. Now safe to import PsychoPy
    from psychopy import core, data, gui, visual
    from respyra.core.display import create_window
```

### Pre-created stimuli

All visual stimuli are created once before the frame loop:

```python
trace = SignalTrace(win, trace_rect=TRACE_RECT, ...)
trace_border = visual.Rect(win, ...)
phase_title = visual.TextStim(win, ...)
target_dot = visual.Circle(win, ...)
```

### Gain perturbation

The displayed waveform is perturbed while the target and error remain veridical:

```python
# Display: apply gain to the visual trace
trace.draw(_apply_gain(buffer, feedback_gain, range_center))

# Target and error: always use true (unperturbed) force
target_force = target_gen.get_target(tracking_t)
error = target_force - force  # true error
```

### Incremental logging with DataLogger

```python
logger = DataLogger(filepath, columns=DATA_COLUMNS)
# Inside frame loop:
logger.log_row(
    timestamp=round(elapsed, 4),
    frame=frame_count,
    force_n=round(force, 4),
    phase='tracking',
    condition=condition_name,
    ...
)
```

### PsychoPy TrialHandler for condition ordering

```python
trial_list = [{'condition': c.name} for c in CONDITIONS]
trials = data.TrialHandler(
    trialList=trial_list, nReps=N_REPS, method='sequential',
)
for trial in trials:
    condition_name = trial['condition']
    ...
```
