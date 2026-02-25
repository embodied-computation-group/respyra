"""Tests for ExperimentConfig dataclass and load_config."""

from __future__ import annotations

import textwrap
from dataclasses import replace

import pytest

from respyra.configs.experiment_config import (
    BeltConfig,
    DisplayConfig,
    DotConfig,
    ExperimentConfig,
    RangeCalConfig,
    TimingConfig,
    TraceConfig,
    TrialConfig,
    load_config,
)
from respyra.core.target_generator import ConditionDef, SegmentDef

# ------------------------------------------------------------------ #
#  ExperimentConfig construction                                       #
# ------------------------------------------------------------------ #


class TestExperimentConfig:
    def test_default_construction(self):
        cfg = ExperimentConfig()
        assert cfg.name == "Breath Tracking Task"
        assert isinstance(cfg.belt, BeltConfig)
        assert isinstance(cfg.display, DisplayConfig)
        assert isinstance(cfg.timing, TimingConfig)

    def test_trace_buffer_size(self):
        cfg = ExperimentConfig(
            trace=TraceConfig(duration_sec=5.0),
            belt=BeltConfig(period_ms=100),
        )
        assert cfg.trace_buffer_size == 50  # 5.0 * (1000 / 100)

    def test_trace_buffer_size_fast_sampling(self):
        cfg = ExperimentConfig(
            trace=TraceConfig(duration_sec=5.0),
            belt=BeltConfig(period_ms=10),
        )
        assert cfg.trace_buffer_size == 500

    def test_data_columns_default(self):
        cfg = ExperimentConfig()
        assert "timestamp" in cfg.data_columns
        assert "force_n" in cfg.data_columns
        assert "phase" in cfg.data_columns

    def test_data_columns_independent(self):
        """Each instance gets its own copy of data_columns."""
        cfg1 = ExperimentConfig()
        cfg2 = ExperimentConfig()
        cfg1.data_columns.append("extra")
        assert "extra" not in cfg2.data_columns


# ------------------------------------------------------------------ #
#  Sub-config defaults                                                 #
# ------------------------------------------------------------------ #


class TestSubConfigs:
    def test_belt_defaults(self):
        bc = BeltConfig()
        assert bc.connection == "ble"
        assert bc.period_ms == 100
        assert bc.channels == [1]

    def test_display_defaults(self):
        dc = DisplayConfig()
        assert dc.fullscr is False
        assert dc.units == "height"

    def test_trace_defaults(self):
        tc = TraceConfig()
        assert tc.color == "lime"
        assert tc.duration_sec == 5.0

    def test_dot_defaults(self):
        dc = DotConfig()
        assert dc.feedback_mode == "graded"
        assert dc.radius == 0.03

    def test_timing_defaults(self):
        tc = TimingConfig()
        assert tc.baseline_duration_sec == 10.0
        assert tc.tracking_duration_sec == 30.0

    def test_range_cal_defaults(self):
        rc = RangeCalConfig()
        assert rc.scale == 0.80
        assert rc.percentile_lo == 5
        assert rc.percentile_hi == 95

    def test_trial_defaults(self):
        tc = TrialConfig()
        assert tc.conditions == []
        assert tc.n_reps == 1
        assert tc.build_conditions is None


# ------------------------------------------------------------------ #
#  replace() overrides                                                 #
# ------------------------------------------------------------------ #


class TestReplace:
    def test_replace_top_level(self):
        cfg = ExperimentConfig(name="Original")
        cfg2 = replace(cfg, name="Modified")
        assert cfg2.name == "Modified"
        assert cfg.name == "Original"  # original untouched

    def test_replace_nested(self):
        cfg = ExperimentConfig()
        cfg2 = replace(cfg, timing=replace(cfg.timing, tracking_duration_sec=60.0))
        assert cfg2.timing.tracking_duration_sec == 60.0
        assert cfg.timing.tracking_duration_sec == 30.0

    def test_replace_with_conditions(self):
        cond = ConditionDef("test", [SegmentDef(0.1, 3)])
        cfg = replace(
            ExperimentConfig(),
            trial=TrialConfig(conditions=[cond] * 5, n_reps=1),
        )
        assert len(cfg.trial.conditions) == 5
        assert cfg.trial.n_reps == 1


# ------------------------------------------------------------------ #
#  load_config                                                         #
# ------------------------------------------------------------------ #


class TestLoadConfig:
    def test_none_returns_default(self):
        cfg = load_config(None)
        assert isinstance(cfg, ExperimentConfig)
        assert cfg.name == "Breath Tracking Task"

    def test_instance_returned_as_is(self):
        original = ExperimentConfig(name="Custom")
        result = load_config(original)
        assert result is original

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent_config.py")

    def test_load_from_file(self, tmp_path):
        config_file = tmp_path / "my_config.py"
        config_file.write_text(
            textwrap.dedent("""\
            from respyra.configs.experiment_config import ExperimentConfig
            CONFIG = ExperimentConfig(name="From File")
            """)
        )
        cfg = load_config(str(config_file))
        assert cfg.name == "From File"

    def test_load_from_file_missing_config_raises(self, tmp_path):
        config_file = tmp_path / "bad_config.py"
        config_file.write_text("X = 42\n")
        with pytest.raises(AttributeError, match="CONFIG"):
            load_config(str(config_file))

    def test_load_from_file_wrong_type_raises(self, tmp_path):
        config_file = tmp_path / "wrong_type.py"
        config_file.write_text("CONFIG = 'not a config'\n")
        with pytest.raises(TypeError, match="ExperimentConfig"):
            load_config(str(config_file))

    def test_load_from_file_sibling_import(self, tmp_path):
        """Config files can import from siblings in the same directory."""
        base = tmp_path / "base.py"
        base.write_text(
            textwrap.dedent("""\
            from respyra.configs.experiment_config import ExperimentConfig
            CONFIG = ExperimentConfig(name="Base")
            """)
        )
        child = tmp_path / "child.py"
        child.write_text(
            textwrap.dedent("""\
            from dataclasses import replace
            from base import CONFIG as _BASE
            CONFIG = replace(_BASE, name="Child")
            """)
        )
        cfg = load_config(str(child))
        assert cfg.name == "Child"

    def test_load_from_file_restores_sys_path(self, tmp_path):
        """sys.path is restored after loading a config file."""
        import sys

        config_file = tmp_path / "my_config.py"
        config_file.write_text(
            textwrap.dedent("""\
            from respyra.configs.experiment_config import ExperimentConfig
            CONFIG = ExperimentConfig(name="PathTest")
            """)
        )
        path_before = list(sys.path)
        load_config(str(config_file))
        assert sys.path == path_before

    def test_load_short_name_demo(self):
        """Short name 'demo' resolves to respyra.configs.demo."""
        cfg = load_config("demo")
        assert isinstance(cfg, ExperimentConfig)
        assert "Demo" in cfg.name or "demo" in cfg.name.lower()

    def test_load_dotted_module_path(self):
        """Dotted module path resolves correctly."""
        cfg = load_config("respyra.configs.demo")
        assert isinstance(cfg, ExperimentConfig)

    def test_load_short_name_nonexistent_raises(self):
        """Short name that doesn't map to a real module raises ImportError."""
        with pytest.raises((ImportError, ModuleNotFoundError)):
            load_config("nonexistent_config_xyz")
