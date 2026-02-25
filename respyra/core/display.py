"""PsychoPy window creation, stimulus helpers, and real-time waveform rendering.

Provides thin wrappers around PsychoPy's ``visual`` and ``monitors`` modules
that enforce project defaults (``'height'`` units, black background,
pre-created stimuli).  Also contains :class:`SignalTrace`, a pre-allocated
``ShapeStim`` for rendering scrolling waveforms without per-frame allocations,
and :func:`draw_signal_trace`, a convenience wrapper with automatic caching.
"""

from psychopy import monitors, visual, event
import numpy as np


# ---------------------------------------------------------------------------
# Monitor profile
# ---------------------------------------------------------------------------

def create_monitor(name: str, width_cm: float, distance_cm: float,
                   size_pix: tuple[int, int]) -> monitors.Monitor:
    """Create, configure, and save a PsychoPy monitor profile.

    Parameters
    ----------
    name : str
        Profile name stored by PsychoPy's monitor center.
    width_cm : float
        Viewable width of the display in centimeters.
    distance_cm : float
        Viewing distance from the participant's eyes to the screen in cm.
    size_pix : tuple of (int, int)
        Screen resolution as (width, height) in pixels.

    Returns
    -------
    monitors.Monitor
    """
    mon = monitors.Monitor(name)
    mon.setWidth(width_cm)
    mon.setDistance(distance_cm)
    mon.setSizePix(size_pix)
    mon.save()
    return mon


# ---------------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------------

def create_window(fullscr: bool = False, monitor=None, units: str = 'height',
                  color: tuple = (-1, -1, -1), **kwargs) -> visual.Window:
    """Create a PsychoPy window with sensible project defaults.

    Parameters
    ----------
    fullscr : bool
        Full-screen mode.  Use False during development, True for data
        collection (enables VSync).
    monitor : str or monitors.Monitor or None
        Monitor profile.  A string is looked up by name; a Monitor object
        is used directly; None falls back to PsychoPy's default.
    units : str
        Coordinate system.  'height' works without calibration and keeps
        aspect-ratio-independent sizing.
    color : tuple
        Background color in PsychoPy RGB (-1 to 1).  Default is black.
    **kwargs
        Forwarded to ``visual.Window`` (e.g. ``screen``, ``size``,
        ``allowGUI``, ``waitBlanking``).

    Returns
    -------
    visual.Window
    """
    # Resolve monitor argument
    if isinstance(monitor, str):
        monitor = monitors.Monitor(monitor)

    win = visual.Window(
        fullscr=fullscr,
        monitor=monitor,
        units=units,
        color=color,
        colorSpace='rgb',
        **kwargs,
    )
    return win


# ---------------------------------------------------------------------------
# Text display
# ---------------------------------------------------------------------------

def show_text_and_wait(win: visual.Window, text: str, key_list: list[str] | None = None,
                      color: str | tuple = 'white') -> str:
    """Draw a text screen and block until the participant presses a key.

    Parameters
    ----------
    win : visual.Window
    text : str
        Message to display (supports newlines).
    key_list : list of str or None
        Acceptable keys.  Defaults to ``['space']``.
    color : str or tuple
        Text color.

    Returns
    -------
    str
        The key that was pressed.
    """
    if key_list is None:
        key_list = ['space']

    msg = visual.TextStim(
        win,
        text=text,
        color=color,
        height=0.04,
        wrapWidth=1.5,
        alignText='center',
    )

    event.clearEvents()
    msg.draw()
    win.flip()

    keys = event.waitKeys(keyList=key_list)
    return keys[0]


# ---------------------------------------------------------------------------
# Real-time signal trace
# ---------------------------------------------------------------------------

class SignalTrace:
    """Pre-created ShapeStim that renders a scrolling waveform.

    Create once before your frame loop, then call :meth:`draw` each frame
    with the latest data.  This avoids re-creating stimulus objects inside
    the render loop.

    Parameters
    ----------
    win : visual.Window
    trace_rect : tuple of (left, bottom, right, top)
        Bounding box in window units for the waveform area.
    y_range : tuple of (float, float)
        Expected (min, max) of the data values.  Used to scale the trace
        vertically within *trace_rect*.
    color : str or tuple
        Line color.
    line_width : float
        Line width in pixels.
    """

    def __init__(self, win, trace_rect=(-0.8, -0.3, 0.8, 0.3),
                 y_range=(0, 50), color='green', line_width=2.0):
        self.win = win
        self.left, self.bottom, self.right, self.top = trace_rect
        self.y_min, self.y_max = y_range
        self.width = self.right - self.left
        self.height = self.top - self.bottom

        # Pre-create ShapeStim with placeholder vertices (a flat line)
        placeholder = [[self.left, self.bottom], [self.right, self.bottom]]
        self._shape = visual.ShapeStim(
            win,
            vertices=placeholder,
            lineColor=color,
            lineWidth=line_width,
            closeShape=False,
            interpolate=True,
        )

    def draw(self, data_points):
        """Update vertices from *data_points* and draw to the back buffer.

        Parameters
        ----------
        data_points : list of float
            Force (or other signal) values.  Mapped left-to-right across
            the trace rectangle, with y scaled to *y_range*.
        """
        n = len(data_points)
        if n < 2:
            return  # need at least 2 points for a line

        # Build vertices: evenly space across x, scale y into the rect
        xs = np.linspace(self.left, self.right, n)

        pts = np.asarray(data_points, dtype=float)
        # Clamp then normalise into 0..1
        y_span = self.y_max - self.y_min
        if y_span == 0:
            normed = np.full_like(pts, 0.5)
        else:
            normed = (pts - self.y_min) / y_span
            normed = np.clip(normed, 0.0, 1.0)

        ys = self.bottom + normed * self.height

        self._shape.vertices = np.column_stack([xs, ys])
        self._shape.draw()


def draw_signal_trace(win, data_points, y_range=(0, 50),
                      trace_rect=(-0.8, -0.3, 0.8, 0.3), color='green',
                      _cache={}):
    """Convenience function: draw a signal trace on *win* this frame.

    Internally caches a :class:`SignalTrace` per window so the ShapeStim
    is created only once — safe to call every frame without allocations.

    Parameters
    ----------
    win : visual.Window
    data_points : list of float
        Signal values to plot.
    y_range : tuple of (float, float)
        Data range for vertical scaling.
    trace_rect : tuple of (left, bottom, right, top)
        Bounding box in window units.
    color : str or tuple
        Line color.
    """
    cache_key = id(win)
    cached = _cache.get(cache_key)

    # Recreate if the visual parameters changed
    if (cached is None
            or cached._y_cfg != (y_range, trace_rect, color)):
        trace = SignalTrace(win, trace_rect=trace_rect,
                            y_range=y_range, color=color)
        trace._y_cfg = (y_range, trace_rect, color)
        _cache[cache_key] = trace
        cached = trace

    cached.draw(data_points)
