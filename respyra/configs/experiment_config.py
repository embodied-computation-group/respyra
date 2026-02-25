"""Experiment configuration dataclass and config loader.

Provides :class:`ExperimentConfig` — a structured container for all
parameters needed to run a breath tracking experiment — and
:func:`load_config` which resolves a config from a module name,
file path, or pre-built instance.

Recipe remixers create a config file in ``experiments/`` that builds
an ``ExperimentConfig`` via :func:`dataclasses.replace`.  Power users
import individual sub-configs to compose custom setups.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from respyra.core.target_generator import ConditionDef

# ------------------------------------------------------------------ #
#  Sub-config dataclasses                                              #
# ------------------------------------------------------------------ #


@dataclass
class BeltConfig:
    """Vernier breath belt connection parameters."""

    connection: str = "ble"
    device_to_open: str | None = "proximity_pairing"
    period_ms: int = 100
    channels: list[int] = field(default_factory=lambda: [1])


@dataclass
class DisplayConfig:
    """PsychoPy window and monitor parameters."""

    fullscr: bool = False
    monitor_name: str = "testMonitor"
    monitor_width_cm: float = 53.0
    monitor_distance_cm: float = 57.0
    monitor_size_pix: tuple[int, int] = (1920, 1080)
    units: str = "height"
    bg_color: tuple[float, float, float] = (-1, -1, -1)


@dataclass
class TraceConfig:
    """Waveform trace display parameters."""

    rect: tuple[float, float, float, float] = (-0.6, -0.15, 0.55, 0.35)
    y_range: tuple[float, float] = (0, 10)
    color: str = "lime"
    border_color: str = "#333333"
    duration_sec: float = 5.0


@dataclass
class DotConfig:
    """Target dot appearance and feedback parameters."""

    radius: float = 0.03
    x_offset: float = 0.05
    color_good: str = "yellow"
    color_bad: str = "red"
    color_mid: str = "orange"
    feedback_mode: str = "graded"
    error_threshold_n: float = 1.0
    error_threshold_mid_n: float = 2.0
    graded_max_error_n: float = 3.0


@dataclass
class TimingConfig:
    """Phase duration parameters (seconds)."""

    range_cal_duration_sec: float = 15.0
    baseline_duration_sec: float = 10.0
    countdown_duration_sec: float = 3.0
    tracking_duration_sec: float = 30.0


@dataclass
class RangeCalConfig:
    """Range calibration parameters."""

    scale: float = 0.80
    percentile_lo: int = 5
    percentile_hi: int = 95
    force_saturation_lo: float = 0.0
    force_saturation_hi: float = 40.0


@dataclass
class TrialConfig:
    """Trial structure parameters."""

    conditions: list[ConditionDef] = field(default_factory=list)
    n_reps: int = 1
    method: str = "sequential"
    build_conditions: Callable[[str], list[ConditionDef]] | None = None


# ------------------------------------------------------------------ #
#  Top-level config                                                    #
# ------------------------------------------------------------------ #

_DEFAULT_DATA_COLUMNS = [
    "timestamp",
    "frame",
    "force_n",
    "target_force",
    "error",
    "compensated_error",
    "phase",
    "condition",
    "trial_num",
    "feedback_gain",
]


@dataclass
class ExperimentConfig:
    """Complete configuration for a breath tracking experiment.

    Sub-configs group related parameters::

        cfg = ExperimentConfig(
            timing=TimingConfig(tracking_duration_sec=40.0),
            trial=TrialConfig(conditions=[...], n_reps=5),
        )

    Override individual fields with :func:`dataclasses.replace`::

        from dataclasses import replace
        cfg2 = replace(cfg, timing=replace(cfg.timing, baseline_duration_sec=15.0))
    """

    name: str = "Breath Tracking Task"
    belt: BeltConfig = field(default_factory=BeltConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    trace: TraceConfig = field(default_factory=TraceConfig)
    dot: DotConfig = field(default_factory=DotConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    range_cal: RangeCalConfig = field(default_factory=RangeCalConfig)
    trial: TrialConfig = field(default_factory=TrialConfig)
    output_dir: str = "data/"
    escape_key: str = "escape"
    data_columns: list[str] = field(default_factory=lambda: list(_DEFAULT_DATA_COLUMNS))

    @property
    def trace_buffer_size(self) -> int:
        """Number of samples visible in the trace window."""
        return int(self.trace.duration_sec * (1000 / self.belt.period_ms))


# ------------------------------------------------------------------ #
#  Config loader                                                       #
# ------------------------------------------------------------------ #


def load_config(source: str | ExperimentConfig | None = None) -> ExperimentConfig:
    """Load an :class:`ExperimentConfig` from *source*.

    Parameters
    ----------
    source : str, ExperimentConfig, or None
        How the config is resolved:

        - ``None`` — returns a default :class:`ExperimentConfig`.
        - :class:`ExperimentConfig` instance — returned as-is.
        - A string ending in ``'.py'`` — treated as a file path.
          The file is imported and its module-level ``CONFIG`` variable
          is returned.  The file's parent directory is temporarily
          added to ``sys.path`` so sibling imports work (e.g.
          ``from defaults import CONFIG``).
        - A dotted module path (e.g. ``'respyra.configs.demo'``) —
          the module is imported and its ``CONFIG`` variable is returned.
        - A short name (e.g. ``'demo'``) — expanded to
          ``'respyra.configs.<name>'`` and imported.

    Returns
    -------
    ExperimentConfig

    Raises
    ------
    FileNotFoundError
        If a ``.py`` path does not exist.
    AttributeError
        If the loaded module has no ``CONFIG`` attribute.
    ImportError
        If a module path cannot be imported.
    """
    if source is None:
        return ExperimentConfig()

    if isinstance(source, ExperimentConfig):
        return source

    # File path
    if source.endswith(".py"):
        return _load_from_file(source)

    # Dotted module path
    if "." in source:
        return _load_from_module(source)

    # Short name → respyra.configs.<name>
    return _load_from_module(f"respyra.configs.{source}")


def _load_from_file(path: str) -> ExperimentConfig:
    """Import a .py file and return its CONFIG object."""
    filepath = Path(path).resolve()
    if not filepath.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")

    module_name = f"_respyra_config_{filepath.stem}"
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load config from: {filepath}")

    module = importlib.util.module_from_spec(spec)

    # Temporarily add parent directory so sibling imports work
    parent = str(filepath.parent)
    added = parent not in sys.path
    if added:
        sys.path.insert(0, parent)
    try:
        spec.loader.exec_module(module)
    finally:
        if added and parent in sys.path:
            sys.path.remove(parent)

    return _extract_config(module, str(filepath))


def _load_from_module(module_path: str) -> ExperimentConfig:
    """Import a module by dotted path and return its CONFIG object."""
    module = importlib.import_module(module_path)
    return _extract_config(module, module_path)


def _extract_config(module: object, source_label: str) -> ExperimentConfig:
    """Extract the CONFIG attribute from a loaded module."""
    if not hasattr(module, "CONFIG"):
        raise AttributeError(
            f"Config module '{source_label}' has no CONFIG attribute. "
            f"Expected a module-level ExperimentConfig named CONFIG."
        )
    cfg = module.CONFIG
    if not isinstance(cfg, ExperimentConfig):
        raise TypeError(
            f"CONFIG in '{source_label}' is {type(cfg).__name__}, expected ExperimentConfig."
        )
    return cfg
