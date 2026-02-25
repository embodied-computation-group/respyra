"""Base experiment configuration with standard parameter values.

This is the starting point for all experiments.  Copy this file or
import its ``CONFIG`` and use :func:`dataclasses.replace` to override
specific parameters::

    from dataclasses import replace
    from defaults import CONFIG as _BASE

    CONFIG = replace(_BASE,
        name="My Study",
        timing=replace(_BASE.timing, tracking_duration_sec=60.0),
    )
"""

from respyra.configs.experiment_config import (
    BeltConfig,
    DisplayConfig,
    DotConfig,
    ExperimentConfig,
    RangeCalConfig,
    TimingConfig,
    TraceConfig,
    TrialConfig,
)
from respyra.configs.presets import PERTURBED_SLOW, SLOW_STEADY

CONFIG = ExperimentConfig(
    name="Breath Tracking Task",
    belt=BeltConfig(
        connection="ble",
        device_to_open="proximity_pairing",
        period_ms=100,
        channels=[1],
    ),
    display=DisplayConfig(
        fullscr=False,
        monitor_name="testMonitor",
        monitor_width_cm=53.0,
        monitor_distance_cm=57.0,
        monitor_size_pix=(1920, 1080),
        units="height",
        bg_color=(-1, -1, -1),
    ),
    trace=TraceConfig(
        rect=(-0.6, -0.15, 0.55, 0.35),
        y_range=(0, 10),
        color="lime",
        border_color="#333333",
        duration_sec=5.0,
    ),
    dot=DotConfig(
        radius=0.03,
        x_offset=0.05,
        color_good="yellow",
        color_bad="red",
        color_mid="orange",
        feedback_mode="graded",
        error_threshold_n=1.0,
        error_threshold_mid_n=2.0,
        graded_max_error_n=3.0,
    ),
    timing=TimingConfig(
        range_cal_duration_sec=15.0,
        baseline_duration_sec=10.0,
        countdown_duration_sec=3.0,
        tracking_duration_sec=30.0,
    ),
    range_cal=RangeCalConfig(
        scale=0.80,
        percentile_lo=5,
        percentile_hi=95,
        force_saturation_lo=0.0,
        force_saturation_hi=40.0,
    ),
    trial=TrialConfig(
        conditions=[SLOW_STEADY, PERTURBED_SLOW],
        n_reps=3,
        method="sequential",
    ),
    output_dir="data/",
    escape_key="escape",
)
