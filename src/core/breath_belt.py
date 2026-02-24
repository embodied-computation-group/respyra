"""Threaded Vernier Go Direct Respiration Belt reader.

Wraps the gdx convenience module with a background thread and queue so that
PsychoPy's frame loop (typically 60 Hz) is never blocked by the sensor's
blocking read() call.

Typical usage
-------------
    with BreathBelt(connection='ble', period_ms=100) as belt:
        # inside PsychoPy frame loop
        sample = belt.get_latest()
        if sample is not None:
            timestamp, force = sample

Or without a context manager:

    belt = BreathBelt()
    belt.start()
    try:
        ...
    finally:
        belt.stop()

Notes
-----
- gdx.read() blocks for the full sampling period (e.g. 100 ms at 10 Hz).
  The background thread absorbs that wait, pushing samples into a
  thread-safe queue that the main thread drains without blocking.
- Always call stop() (or use the context manager) to ensure the device
  is cleanly disconnected.  Failure to do so leaves the belt streaming,
  requiring a physical power-cycle.
- The gdx wrapper uses *class-level* state, so only one BreathBelt
  instance should exist at a time.
- **Windows BLE + PsychoPy:** On Windows, importing PsychoPy
  (pyglet/wxPython) puts the main thread into COM STA mode, which
  breaks Bleak's BLE scanner.  Bleak also requires the main thread
  for Windows Runtime callbacks.  Therefore, ``start()`` must be
  called on the main thread *before* PsychoPy is imported.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Optional

from src.core.gdx import gdx as _gdx_module

logger = logging.getLogger(__name__)


class BreathBeltError(Exception):
    """Raised when the belt encounters a fatal error."""


class BreathBelt:
    """Non-blocking interface to the Vernier Go Direct Respiration Belt.

    Parameters
    ----------
    connection : str
        ``'ble'`` or ``'usb'``.
    device_to_open : str or None
        Device identifier passed to ``gdx.open()``.  ``'proximity_pairing'``
        connects to the nearest BLE device.  A specific name like
        ``'GDX-RB 081000A1'`` targets a known belt.  ``None`` auto-connects
        for USB (single device) or prompts for BLE (**avoid** in automated
        scripts).
    period_ms : int
        Sampling interval in milliseconds.  Minimum is 10 (100 Hz).
        Default 100 (10 Hz) gives good resolution for respiration waveforms.
    sensors : list[int]
        Channel numbers to enable.  Default ``[1]`` enables the raw Force
        channel, which is the primary respiration signal.
    """

    def __init__(
        self,
        connection: str = "ble",
        device_to_open: str = "proximity_pairing",
        period_ms: int = 100,
        sensors: list[int] | None = None,
    ) -> None:
        if sensors is None:
            sensors = [1]
        if period_ms < 10:
            raise ValueError(
                f"period_ms={period_ms} is below the 10 ms minimum supported "
                "by Go Direct hardware."
            )

        self._connection = connection
        self._device_to_open = device_to_open
        self._period_ms = period_ms
        self._sensors = list(sensors)

        # Internals -- populated by start()
        self._gdx: Optional[_gdx_module.gdx] = None
        self._queue: queue.Queue[tuple[float, float]] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._started = False

        # Error reporting from the reader thread
        self._error: Optional[BaseException] = None
        self._error_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Open the device, configure sensors, and launch the reader thread.

        On Windows, Bleak's BLE scanner requires the main thread *and*
        a COM MTA apartment.  Importing PsychoPy sets COM to STA, so
        ``start()`` must be called **before** ``import psychopy``.

        Raises
        ------
        BreathBeltError
            If the belt is already started or the device fails to open.
        """
        if self._started:
            raise BreathBeltError("BreathBelt is already started.")

        logger.info(
            "Opening belt: connection=%s, device=%s, period=%d ms, sensors=%s",
            self._connection,
            self._device_to_open,
            self._period_ms,
            self._sensors,
        )

        try:
            self._init_device()
        except BreathBeltError:
            self._cleanup_gdx()
            raise
        except Exception as exc:
            self._cleanup_gdx()
            raise BreathBeltError(
                f"Failed to initialise belt: {exc}"
            ) from exc

        self._stop_event.clear()
        self._error = None

        self._thread = threading.Thread(
            target=self._reader_loop,
            name="BreathBelt-reader",
            daemon=True,
        )
        self._started = True
        self._thread.start()
        logger.info("Reader thread started.")

    def get_latest(self) -> Optional[tuple[float, float]]:
        """Return the most recent sample, discarding older ones.

        Returns
        -------
        tuple[float, float] or None
            ``(timestamp, force_value)`` where *timestamp* is
            ``time.time()`` at the moment ``gdx.read()`` returned, and
            *force_value* is the reading (in Newtons) from the first
            enabled channel.  Returns ``None`` if no samples are available.

        Raises
        ------
        BreathBeltError
            If the reader thread has recorded an error.
        """
        self._check_error()

        latest = None
        try:
            while True:
                latest = self._queue.get_nowait()
        except queue.Empty:
            pass
        return latest

    def get_all(self) -> list[tuple[float, float]]:
        """Drain and return all queued samples since the last call.

        Returns
        -------
        list[tuple[float, float]]
            A list of ``(timestamp, force_value)`` tuples in chronological
            order.  May be empty if no new samples have arrived.

        Raises
        ------
        BreathBeltError
            If the reader thread has recorded an error.
        """
        self._check_error()

        samples: list[tuple[float, float]] = []
        try:
            while True:
                samples.append(self._queue.get_nowait())
        except queue.Empty:
            pass
        return samples

    def stop(self) -> None:
        """Signal the reader thread to stop, join it, and close the device.

        Safe to call multiple times -- subsequent calls are no-ops.
        """
        if not self._started:
            return

        logger.info("Stopping reader thread...")
        self._stop_event.set()

        if self._thread is not None and self._thread.is_alive():
            # Allow up to 2x the sampling period + a generous margin
            # for the blocking read() to return.
            join_timeout = (self._period_ms / 1000.0) * 2 + 1.0
            self._thread.join(timeout=join_timeout)
            if self._thread.is_alive():
                logger.warning(
                    "Reader thread did not exit within %.1f s. "
                    "It will be abandoned (daemon thread).",
                    join_timeout,
                )

        self._cleanup_gdx()
        self._started = False
        logger.info("Belt stopped and device closed.")

    @property
    def is_running(self) -> bool:
        """True if the reader thread is alive and no error has occurred."""
        return (
            self._started
            and self._thread is not None
            and self._thread.is_alive()
            and self._error is None
        )

    @property
    def has_error(self) -> bool:
        """True if the reader thread has recorded an error."""
        with self._error_lock:
            return self._error is not None

    @property
    def error(self) -> Optional[BaseException]:
        """The exception recorded by the reader thread, or None."""
        with self._error_lock:
            return self._error

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "BreathBelt":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
        return None  # do not suppress exceptions

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _init_device(self) -> None:
        """Open the device, configure sensors, and begin streaming.

        Must run on the main thread — Bleak's BLE scanner requires it
        for Windows Runtime callbacks.
        """
        self._gdx = _gdx_module.gdx()
        print(f"[belt] Scanning {self._connection.upper()}...")
        self._gdx.open(
            connection=self._connection,
            device_to_open=self._device_to_open,
        )
        # gdx.open() silently fails (prints a message but doesn't raise)
        # when no device is found.  Check the class-level devices list.
        if not _gdx_module.gdx.devices:
            raise BreathBeltError(
                f"No Go Direct device found via {self._connection}. "
                "Is the belt powered on and in range?"
            )
        print(f"[belt] Device found. Configuring sensors {self._sensors}...")
        self._gdx.select_sensors(self._sensors)
        print(f"[belt] Starting data collection at {self._period_ms} ms...")
        self._gdx.start(self._period_ms)

    def _reader_loop(self) -> None:
        """Background loop: read from gdx and push samples to the queue.

        Runs until ``_stop_event`` is set or an unrecoverable error occurs.
        Exceptions are stored on ``self._error`` rather than propagated,
        because this runs in a daemon thread.
        """
        logger.debug("Reader loop entered.")
        try:
            while not self._stop_event.is_set():
                measurements = self._gdx.read()
                if measurements is None:
                    # Device disconnected or buffer empty -- treat as fatal.
                    raise BreathBeltError(
                        "gdx.read() returned None (device disconnected?)."
                    )

                timestamp = time.time()
                force_value = measurements[0]
                self._queue.put((timestamp, force_value))
        except Exception as exc:
            # Only record the error if we were not asked to stop.
            # During shutdown, gdx.read() may raise as the device closes;
            # that is expected and not a real error.
            if not self._stop_event.is_set():
                with self._error_lock:
                    self._error = exc
                logger.error("Reader thread error: %s", exc, exc_info=True)
        finally:
            logger.debug("Reader loop exited.")

    def _cleanup_gdx(self) -> None:
        """Stop data collection and disconnect the device.

        Safe to call even if the gdx object is partially initialised.
        """
        if self._gdx is None:
            return
        try:
            self._gdx.stop()
        except Exception:
            logger.debug("gdx.stop() raised during cleanup.", exc_info=True)
        try:
            self._gdx.close()
        except Exception:
            logger.debug("gdx.close() raised during cleanup.", exc_info=True)
        self._gdx = None

    def _check_error(self) -> None:
        """Raise if the reader thread has encountered an error."""
        with self._error_lock:
            if self._error is not None:
                raise BreathBeltError(
                    f"Reader thread failed: {self._error}"
                ) from self._error
