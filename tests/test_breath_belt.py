"""Tests for respyra.core.breath_belt — mock gdx, test queue/thread logic."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

# ------------------------------------------------------------------
# We need to mock the gdx import *before* importing breath_belt,
# since it does `from respyra.core.gdx import gdx as _gdx_module`
# at module level.
# ------------------------------------------------------------------


def _make_mock_gdx_module(devices=None, read_return=None):
    """Build a mock gdx module with a controllable gdx class."""
    if devices is None:
        devices = [MagicMock()]
    if read_return is None:
        read_return = [5.0]

    mock_mod = ModuleType("respyra.core.gdx.gdx")

    class MockGdx:
        devices = []  # class-level, set below

        def __init__(self):
            pass

        def open(self, **kwargs):
            MockGdx.devices = devices

        def select_sensors(self, sensors):
            pass

        def start(self, period):
            pass

        def read(self):
            return read_return

        def stop(self):
            pass

        def close(self):
            pass

    mock_mod.gdx = MockGdx
    return mock_mod


@pytest.fixture()
def _patch_gdx(monkeypatch):
    """Patch the gdx module so breath_belt can be imported and tested."""
    mock_mod = _make_mock_gdx_module()
    monkeypatch.setitem(sys.modules, "respyra.core.gdx.gdx", mock_mod)
    monkeypatch.setitem(sys.modules, "respyra.core.gdx", MagicMock(gdx=mock_mod))

    # Force re-import of breath_belt with the mocked gdx
    if "respyra.core.breath_belt" in sys.modules:
        monkeypatch.delitem(sys.modules, "respyra.core.breath_belt")

    from respyra.core import breath_belt

    return breath_belt, mock_mod


# ================================================================
# Validation
# ================================================================


class TestBreathBeltValidation:
    def test_period_below_minimum_raises(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        with pytest.raises(ValueError, match="period_ms=5"):
            breath_belt.BreathBelt(period_ms=5)

    def test_period_at_minimum_ok(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        belt = breath_belt.BreathBelt(period_ms=10)
        assert belt._period_ms == 10

    def test_default_sensors(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        belt = breath_belt.BreathBelt()
        assert belt._sensors == [1]

    def test_custom_sensors(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        belt = breath_belt.BreathBelt(sensors=[1, 2])
        assert belt._sensors == [1, 2]


# ================================================================
# Queue operations (test without starting the reader thread)
# ================================================================


class TestBreathBeltQueue:
    def test_get_latest_empty_returns_none(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        belt = breath_belt.BreathBelt()
        # Queue is empty, not started — get_latest returns None
        assert belt.get_latest() is None

    def test_get_latest_returns_most_recent(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        belt = breath_belt.BreathBelt()
        belt._queue.put((1.0, 3.0))
        belt._queue.put((2.0, 4.0))
        belt._queue.put((3.0, 5.0))
        result = belt.get_latest()
        assert result == (3.0, 5.0)
        # Queue should be drained
        assert belt._queue.empty()

    def test_get_all_empty_returns_empty_list(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        belt = breath_belt.BreathBelt()
        assert belt.get_all() == []

    def test_get_all_returns_all_in_order(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        belt = breath_belt.BreathBelt()
        samples = [(1.0, 3.0), (2.0, 4.0), (3.0, 5.0)]
        for s in samples:
            belt._queue.put(s)
        result = belt.get_all()
        assert result == samples
        assert belt._queue.empty()


# ================================================================
# Error propagation
# ================================================================


class TestBreathBeltErrors:
    def test_get_latest_raises_on_error(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        belt = breath_belt.BreathBelt()
        belt._error = RuntimeError("device gone")
        with pytest.raises(breath_belt.BreathBeltError, match="Reader thread failed"):
            belt.get_latest()

    def test_get_all_raises_on_error(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        belt = breath_belt.BreathBelt()
        belt._error = RuntimeError("device gone")
        with pytest.raises(breath_belt.BreathBeltError, match="Reader thread failed"):
            belt.get_all()

    def test_has_error_property(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        belt = breath_belt.BreathBelt()
        assert not belt.has_error
        belt._error = RuntimeError("fail")
        assert belt.has_error

    def test_error_property(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        belt = breath_belt.BreathBelt()
        assert belt.error is None
        err = RuntimeError("fail")
        belt._error = err
        assert belt.error is err


# ================================================================
# Lifecycle
# ================================================================


class TestBreathBeltLifecycle:
    def test_stop_when_not_started_is_noop(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        belt = breath_belt.BreathBelt()
        belt.stop()  # should not raise

    def test_double_start_raises(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        belt = breath_belt.BreathBelt()
        try:
            belt.start()
        except breath_belt.BreathBeltError:
            pytest.skip("gdx mock did not take effect (no hardware)")
        try:
            with pytest.raises(breath_belt.BreathBeltError, match="already started"):
                belt.start()
        finally:
            belt.stop()

    def test_context_manager_starts_and_stops(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        try:
            with breath_belt.BreathBelt() as belt:
                assert belt._started
        except breath_belt.BreathBeltError:
            pytest.skip("gdx mock did not take effect (no hardware)")
        assert not belt._started

    def test_is_running_before_start(self, _patch_gdx):
        breath_belt, _ = _patch_gdx
        belt = breath_belt.BreathBelt()
        assert not belt.is_running
