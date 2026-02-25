# Full Experiment: Breath Tracking Task

**Script:** `respyra/scripts/breath_tracking_task.py`

**What it demonstrates:** The complete respiratory tracking experiment with calibration, multi-condition trials, and data logging.

## How to run

```bash
# Default configuration
respyra-task

# Built-in config by short name
respyra-task --config demo
respyra-task --config validation_study

# Custom config file
respyra-task --config experiments/my_study.py
```

To customize the experiment, see the {doc}`../creating_experiments` tutorial.

## Architecture overview

The experiment is built from composable phase functions in {mod}`respyra.core.runner`:

1. **Belt connection** (`connect_belt`) — connects before PsychoPy import (Windows BLE requirement)
2. **Display setup** (`setup_display`) — monitor profile, window, pre-created stimuli
3. **Participant dialog** (`run_participant_dialog`) — collects participant ID and session number
4. **Range calibration** (`run_range_calibration`) — 15 s of deep breaths to establish breathing range
5. **Trial loop** — for each condition:
   - `run_baseline` (10 s) → `run_countdown` (3 s) → `run_tracking` (30 s) → `show_trial_feedback`
6. **Cleanup** — belt stop, file close, window close (in `finally` block)

All phases share state via an {class}`~respyra.core.runner.ExperimentState` dataclass.

## Key code patterns

### Belt-before-PsychoPy import order

```python
from respyra.core.runner import connect_belt, setup_display

# 1. Connect belt BEFORE importing PsychoPy
belt = connect_belt(cfg)

# 2. Now safe to import PsychoPy and set up display
win, stimuli = setup_display(cfg)
```

### Configuration-driven setup

All parameters come from an {class}`~respyra.configs.experiment_config.ExperimentConfig`:

```python
from respyra.configs.experiment_config import load_config
from respyra.core.runner import run_experiment

cfg = load_config("demo")  # or a file path, or an ExperimentConfig instance
run_experiment(cfg)
```

### Pre-created stimuli

All visual stimuli are created once by `setup_display` before the frame loop:

```python
win, stimuli = setup_display(cfg)
# stimuli["trace"], stimuli["trace_border"], stimuli["phase_title"],
# stimuli["status_text"], stimuli["countdown_text"], stimuli["target_dot"]
```

### Gain perturbation

The displayed waveform is perturbed; the dot color reflects the visual (compensated) error:

```python
from respyra.core.runner import apply_gain

# Display: apply gain to the visual trace
stimuli["trace"].draw(apply_gain(buffer, feedback_gain, range_center))

# Target position uses true force; dot color uses visual error
target_force = target_gen.get_target(tracking_t)
error = target_force - force  # true (physical) error
visual_force = center + feedback_gain * (force - center)
compensated_error = target_force - visual_force  # visual error (drives dot color)
```

### Incremental logging with DataLogger

```python
logger = DataLogger(filepath, columns=cfg.data_columns)
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
trial_list = [{'condition': c.name} for c in conditions]
trials = data.TrialHandler(
    trialList=trial_list, nReps=cfg.trial.n_reps, method=cfg.trial.method,
)
for trial in trials:
    condition_name = trial['condition']
    ...
```
