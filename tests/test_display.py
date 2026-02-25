"""Tests for respyra.core.display — mock PsychoPy, test scaling math."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ================================================================
# SignalTrace scaling logic
# ================================================================


class TestSignalTrace:
    @pytest.fixture()
    def mock_win(self):
        return MagicMock()

    @pytest.fixture()
    def trace(self, mock_win):
        from respyra.core.display import SignalTrace

        return SignalTrace(
            mock_win,
            trace_rect=(-0.5, -0.25, 0.5, 0.25),
            y_range=(0.0, 10.0),
        )

    def test_fewer_than_2_points_no_draw(self, trace):
        trace.draw([5.0])
        # ShapeStim.draw should not be called
        trace._shape.draw.assert_not_called()

    def test_empty_data_no_draw(self, trace):
        trace.draw([])
        trace._shape.draw.assert_not_called()

    def test_two_points_draws(self, trace):
        trace.draw([0.0, 10.0])
        trace._shape.draw.assert_called_once()

    def test_vertices_x_range(self, trace):
        trace.draw([5.0, 5.0, 5.0, 5.0])
        vertices = trace._shape.vertices
        xs = vertices[:, 0]
        np.testing.assert_allclose(xs[0], -0.5)
        np.testing.assert_allclose(xs[-1], 0.5)

    def test_vertices_y_scaling_min_max(self, trace):
        # y_range = (0, 10), trace_rect bottom=-0.25, top=0.25
        trace.draw([0.0, 10.0])
        vertices = trace._shape.vertices
        ys = vertices[:, 1]
        np.testing.assert_allclose(ys[0], -0.25)  # min → bottom
        np.testing.assert_allclose(ys[1], 0.25)  # max → top

    def test_vertices_y_scaling_midpoint(self, trace):
        trace.draw([5.0, 5.0])
        vertices = trace._shape.vertices
        ys = vertices[:, 1]
        np.testing.assert_allclose(ys, 0.0)  # midpoint of rect

    def test_values_clamped_below_range(self, trace):
        trace.draw([-5.0, -5.0])
        vertices = trace._shape.vertices
        ys = vertices[:, 1]
        np.testing.assert_allclose(ys, -0.25)  # clamped to bottom

    def test_values_clamped_above_range(self, trace):
        trace.draw([20.0, 20.0])
        vertices = trace._shape.vertices
        ys = vertices[:, 1]
        np.testing.assert_allclose(ys, 0.25)  # clamped to top

    def test_zero_y_span_maps_to_midpoint(self, mock_win):
        from respyra.core.display import SignalTrace

        trace = SignalTrace(
            mock_win,
            trace_rect=(-0.5, -0.25, 0.5, 0.25),
            y_range=(5.0, 5.0),  # zero span
        )
        trace.draw([5.0, 5.0])
        vertices = trace._shape.vertices
        ys = vertices[:, 1]
        np.testing.assert_allclose(ys, 0.0)  # midpoint


# ================================================================
# draw_signal_trace cache logic
# ================================================================


class TestDrawSignalTraceCache:
    def test_cache_creates_trace_on_first_call(self):
        from respyra.core import display

        display._signal_trace_cache.clear()
        mock_win = MagicMock()
        display.draw_signal_trace(mock_win, [1.0, 2.0, 3.0])
        assert id(mock_win) in display._signal_trace_cache

    def test_cache_reuses_trace_on_same_params(self):
        from respyra.core import display

        display._signal_trace_cache.clear()
        mock_win = MagicMock()
        display.draw_signal_trace(mock_win, [1.0, 2.0])
        first = display._signal_trace_cache[id(mock_win)]
        display.draw_signal_trace(mock_win, [3.0, 4.0])
        second = display._signal_trace_cache[id(mock_win)]
        assert first is second

    def test_cache_invalidated_on_param_change(self):
        from respyra.core import display

        display._signal_trace_cache.clear()
        mock_win = MagicMock()
        display.draw_signal_trace(mock_win, [1.0, 2.0], y_range=(0, 10))
        first = display._signal_trace_cache[id(mock_win)]
        display.draw_signal_trace(mock_win, [1.0, 2.0], y_range=(0, 50))
        second = display._signal_trace_cache[id(mock_win)]
        assert first is not second


# ================================================================
# show_text_and_wait
# ================================================================


class TestShowTextAndWait:
    def test_returns_first_key(self):

        from respyra.core.display import show_text_and_wait

        mock_win = MagicMock()
        with patch("respyra.core.display.event") as mock_event:
            mock_event.waitKeys.return_value = ["space"]
            result = show_text_and_wait(mock_win, "Hello")
        assert result == "space"

    def test_default_key_list_is_space(self):

        from respyra.core.display import show_text_and_wait

        mock_win = MagicMock()
        with patch("respyra.core.display.event") as mock_event:
            mock_event.waitKeys.return_value = ["space"]
            show_text_and_wait(mock_win, "Hello")
            mock_event.waitKeys.assert_called_with(keyList=["space"])
