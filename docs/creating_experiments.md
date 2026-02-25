# Creating Experiments

This tutorial walks through creating custom respiratory tracking experiments with respyra, from running a built-in config to composing a fully custom experiment flow.

## Running built-in configs

The fastest path — run a pre-defined experiment with no code changes:

```bash
# Built-in config by short name
respyra-task --config demo
respyra-task --config validation_study

# Or use a file path
respyra-task --config experiments/demo.py
```

The `--config` flag accepts three forms:

| Form | Example | Resolution |
|------|---------|------------|
| Short name | `demo` | Imports `respyra.configs.demo` |
| Dotted path | `respyra.configs.demo` | Imports the module directly |
| File path | `experiments/my_study.py` | Loads the `.py` file |

Every config module must export a module-level variable named `CONFIG` — an {class}`~respyra.configs.experiment_config.ExperimentConfig` instance.

```{note}
Config files are standard Python modules and are executed when loaded. Only use config files from trusted sources.
```

## Creating a custom config

The recommended workflow: start from the base defaults and override what you need using {func}`dataclasses.replace`.

### 1. Create a config file

Create a file in `experiments/` (or anywhere you like):

```python
# experiments/my_study.py
"""My first custom experiment."""

from dataclasses import replace
from defaults import CONFIG as _BASE

from respyra.configs.experiment_config import TrialConfig
from respyra.configs.presets import slow_steady

# 5 cycles at 0.1 Hz = 50 seconds per trial
MY_CONDITION = slow_steady(n_cycles=5)

CONFIG = replace(
    _BASE,
    name="My Study",
    timing=replace(_BASE.timing, tracking_duration_sec=50.0),
    display=replace(_BASE.display, fullscr=True),
    trial=TrialConfig(
        conditions=[MY_CONDITION] * 4,
        n_reps=1,
        method="sequential",
    ),
)
```

The `experiments/defaults.py` file provides sensible base parameters — `from defaults import CONFIG` works because `load_config` temporarily adds the file's parent directory to `sys.path`.

### 2. Run it

```bash
respyra-task --config experiments/my_study.py
```

### What you can override

Each sub-config groups related parameters. Override any of them with nested `replace()` calls:

```python
from dataclasses import replace
from defaults import CONFIG as _BASE

CONFIG = replace(
    _BASE,
    # Change the experiment name
    name="Slow Breathing Study",

    # Change timing
    timing=replace(_BASE.timing,
        baseline_duration_sec=15.0,
        tracking_duration_sec=60.0,
    ),

    # Change display
    display=replace(_BASE.display,
        fullscr=True,
        monitor_size_pix=(2560, 1440),
    ),

    # Change the belt
    belt=replace(_BASE.belt, connection="usb"),
)
```

## Using condition presets

The {mod}`respyra.configs.presets` module provides factory functions for common breathing paradigms:

```python
from respyra.configs.presets import slow_steady, perturbed_slow, mixed_rhythm

# Factory functions — customize parameters
easy = slow_steady(freq_hz=0.1, n_cycles=3)          # 30 s trial
hard = slow_steady(freq_hz=0.15, n_cycles=4)         # 26.7 s trial
perturbed = perturbed_slow(feedback_gain=2.0)         # 2x visual gain (default is 1.5x)
mixed = mixed_rhythm(freq_slow=0.1, freq_fast=0.25)   # multi-segment

# Pre-built constants — standard defaults
from respyra.configs.presets import SLOW_STEADY, PERTURBED_SLOW, MIXED_RHYTHM
```

### Building from scratch

For full control, use {class}`~respyra.core.target_generator.ConditionDef` and {class}`~respyra.core.target_generator.SegmentDef` directly:

```python
from respyra.core.target_generator import ConditionDef, SegmentDef

# Graded gain levels for dose-response designs
conditions = [
    ConditionDef("gain_1.0", [SegmentDef(0.1, 3)], feedback_gain=1.0),
    ConditionDef("gain_1.5", [SegmentDef(0.1, 3)], feedback_gain=1.5),
    ConditionDef("gain_2.0", [SegmentDef(0.1, 3)], feedback_gain=2.0),
    ConditionDef("gain_2.5", [SegmentDef(0.1, 3)], feedback_gain=2.5),
]

# Fast breathing with multiple segments
fast_protocol = ConditionDef("fast_ramp", [
    SegmentDef(0.2, 2),   # 10 s at 0.2 Hz
    SegmentDef(0.3, 3),   # 10 s at 0.3 Hz
    SegmentDef(0.4, 4),   # 10 s at 0.4 Hz
])
```

Use integer cycle counts per segment to ensure phase continuity at boundaries — the waveform loops seamlessly.

## Counterbalanced designs

For studies requiring counterbalancing across sessions, define a `build_conditions()` function and pass it to {class}`~respyra.configs.experiment_config.TrialConfig`:

```python
# experiments/my_counterbalanced_study.py
from dataclasses import replace
from defaults import CONFIG as _BASE

from respyra.configs.experiment_config import TrialConfig
from respyra.configs.presets import perturbed_slow, slow_steady

SLOW_4 = slow_steady(n_cycles=4)
PERTURBED_4 = perturbed_slow(n_cycles=4, feedback_gain=2.0)
BLOCK_SIZE = 6


def build_conditions(session_num):
    """Counterbalance starting condition across sessions.

    Odd sessions (1, 3): slow_steady block first.
    Even sessions (2, 4): perturbed block first.
    """
    if int(session_num) % 2 == 1:
        return [SLOW_4] * BLOCK_SIZE + [PERTURBED_4] * BLOCK_SIZE
    else:
        return [PERTURBED_4] * BLOCK_SIZE + [SLOW_4] * BLOCK_SIZE


CONFIG = replace(
    _BASE,
    name="Counterbalanced Study",
    timing=replace(_BASE.timing, tracking_duration_sec=40.0),
    trial=TrialConfig(
        conditions=build_conditions(1),  # default for Session 1
        n_reps=1,
        method="sequential",
        build_conditions=build_conditions,  # called at runtime with actual session
    ),
)
```

When `build_conditions` is set, the runner calls it at runtime with the session number entered in the participant dialog, overriding the static `conditions` list.

See `experiments/validation_study.py` for a complete working example.

## Custom experiment flows

For experiments that deviate from the standard flow (e.g., skipping baseline, adding custom phases, or running multiple calibrations), import individual phase functions from {mod}`respyra.core.runner`:

```python
from respyra.core.runner import (
    ExperimentState,
    connect_belt,
    setup_display,
    run_participant_dialog,
    run_range_calibration,
    run_baseline,
    run_countdown,
    run_tracking,
    show_trial_feedback,
    show_end_screen,
)
from respyra.configs.experiment_config import ExperimentConfig

cfg = ExperimentConfig(...)

# Compose your own flow
belt = connect_belt(cfg)

from psychopy import core
from respyra.core.data_logger import DataLogger, create_session_file
from collections import deque

win, stimuli = setup_display(cfg)
exp_info = run_participant_dialog(cfg)
filepath = create_session_file(exp_info["participant"], exp_info["session"])
logger = DataLogger(filepath, columns=cfg.data_columns)

state = ExperimentState(
    belt=belt, win=win, logger=logger,
    clock=core.Clock(), buffer=deque(maxlen=cfg.trace_buffer_size),
    stimuli=stimuli,
)

# Example: skip baseline, run calibration, then just tracking
run_range_calibration(state, cfg)
for trial_num in range(1, 6):
    # ... run_countdown, run_tracking, etc.
    pass
```

Each phase function takes an `ExperimentState` and `ExperimentConfig`, mutates the state, and returns status flags. See the {mod}`API reference <respyra.core.runner>` for full signatures.

## Configuration reference

### ExperimentConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | `"Breath Tracking Task"` | Experiment name (shown in dialogs) |
| `belt` | `BeltConfig` | See below | Belt connection parameters |
| `display` | `DisplayConfig` | See below | PsychoPy window settings |
| `trace` | `TraceConfig` | See below | Waveform display |
| `dot` | `DotConfig` | See below | Target dot appearance and feedback |
| `timing` | `TimingConfig` | See below | Phase durations |
| `range_cal` | `RangeCalConfig` | See below | Range calibration |
| `trial` | `TrialConfig` | See below | Trial structure and conditions |
| `output_dir` | `str` | `"data/"` | Output directory for CSV files |
| `escape_key` | `str` | `"escape"` | Key to abort the experiment |
| `data_columns` | `list[str]` | 10 standard columns | Column names for the output CSV |

### BeltConfig

| Field | Default | Description |
|-------|---------|-------------|
| `connection` | `"ble"` | Connection type: `"ble"` or `"usb"` |
| `device_to_open` | `"proximity_pairing"` | BLE device selection strategy |
| `period_ms` | `100` | Sampling interval in ms (100 = 10 Hz) |
| `channels` | `[1]` | Sensor channels (1 = Force in Newtons) |

### DisplayConfig

| Field | Default | Description |
|-------|---------|-------------|
| `fullscr` | `False` | Full-screen mode (set `True` for data collection) |
| `monitor_name` | `"testMonitor"` | PsychoPy monitor profile name |
| `monitor_width_cm` | `53.0` | Physical screen width in cm |
| `monitor_distance_cm` | `57.0` | Viewing distance in cm |
| `monitor_size_pix` | `(1920, 1080)` | Screen resolution |
| `units` | `"height"` | PsychoPy coordinate system |
| `bg_color` | `(-1, -1, -1)` | Background color (black) |

### TraceConfig

| Field | Default | Description |
|-------|---------|-------------|
| `rect` | `(-0.6, -0.15, 0.55, 0.35)` | Trace area (left, bottom, right, top) |
| `y_range` | `(0, 10)` | Initial force range (overridden after calibration) |
| `color` | `"lime"` | Waveform color |
| `border_color` | `"#333333"` | Trace border color |
| `duration_sec` | `5.0` | Seconds of signal visible on screen |

### DotConfig

| Field | Default | Description |
|-------|---------|-------------|
| `radius` | `0.03` | Dot radius (height units) |
| `x_offset` | `0.05` | Offset right of trace edge |
| `color_good` | `"yellow"` | Good tracking color |
| `color_bad` | `"red"` | Poor tracking color |
| `color_mid` | `"orange"` | Moderate tracking color (trinary mode) |
| `feedback_mode` | `"graded"` | `"graded"`, `"binary"`, or `"trinary"` |
| `error_threshold_n` | `1.0` | Good/bad cutoff in Newtons |
| `error_threshold_mid_n` | `2.0` | Mid/bad cutoff in Newtons |
| `graded_max_error_n` | `3.0` | Error at which dot is fully red |

### TimingConfig

| Field | Default | Description |
|-------|---------|-------------|
| `range_cal_duration_sec` | `15.0` | Range calibration duration |
| `baseline_duration_sec` | `10.0` | Baseline per trial |
| `countdown_duration_sec` | `3.0` | Countdown per trial |
| `tracking_duration_sec` | `30.0` | Tracking per trial |

### RangeCalConfig

| Field | Default | Description |
|-------|---------|-------------|
| `scale` | `0.80` | Fraction of range used for target amplitude |
| `percentile_lo` | `5` | Lower percentile for outlier rejection |
| `percentile_hi` | `95` | Upper percentile for outlier rejection |
| `force_saturation_lo` | `0.0` | Sensor floor warning threshold |
| `force_saturation_hi` | `40.0` | Sensor ceiling warning threshold |

### TrialConfig

| Field | Default | Description |
|-------|---------|-------------|
| `conditions` | `[]` | List of `ConditionDef` objects |
| `n_reps` | `1` | Repetitions per condition |
| `method` | `"sequential"` | `"sequential"` or `"random"` |
| `build_conditions` | `None` | Optional function `(session) -> [ConditionDef]` for counterbalancing |
