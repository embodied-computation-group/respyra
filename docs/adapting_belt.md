# Adapting to a Different Respiratory Sensor

respyra's architecture separates the belt I/O from the experiment logic, making it possible to substitute a different respiratory sensor. This guide explains the interface contract and shows how to implement a custom sensor class.

## The BreathBelt interface contract

The experiment scripts interact with the belt through these methods and properties:

### `start()`

Open the device, configure sensors, and begin streaming in a background thread. Must be called on the main thread (required for BLE on Windows).

### `get_latest() → tuple[float, float] | None`

Return the most recent `(timestamp, force_value)` sample, discarding older ones. Returns `None` if no new data is available. This is non-blocking and safe to call every frame.

### `get_all() → list[tuple[float, float]]`

Drain and return all queued samples since the last call. Returns a list of `(timestamp, force_value)` tuples in chronological order. May be empty.

### `stop()`

Signal the background thread to stop, join it, and close the device. Safe to call multiple times.

### `is_running` (property)

`True` if the background thread is alive and no error has occurred.

### Context manager

`BreathBelt` supports `with` statements for automatic cleanup:

```python
with BreathBelt() as belt:
    sample = belt.get_latest()
```

## Thread + queue architecture

The current implementation uses a background thread that calls the sensor's blocking `read()` in a loop and pushes `(timestamp, force)` tuples into a `queue.Queue`. The main thread (running PsychoPy's frame loop) drains the queue via `get_latest()` or `get_all()` without blocking.

```
┌──────────────┐          ┌──────────────┐
│ Reader thread │  queue   │  Main thread  │
│               │ ───────► │  (PsychoPy)   │
│  sensor.read()│          │  get_latest() │
└──────────────┘          └──────────────┘
```

This pattern is necessary because:
- The sensor read call blocks for the full sampling period (e.g., 100 ms)
- PsychoPy's frame loop must run at the monitor refresh rate (typically 60 Hz ≈ 16.7 ms)
- A blocking read inside the frame loop would cause frame drops

## Implementing a custom sensor

To substitute a different sensor, create a class that matches the interface above. Here is a skeleton:

```python
import queue
import threading
import time


class CustomSensor:
    """Drop-in replacement for BreathBelt using a hypothetical sensor."""

    def __init__(self, port: str = "/dev/ttyUSB0", sample_rate_hz: float = 10.0):
        self._port = port
        self._period = 1.0 / sample_rate_hz
        self._queue: queue.Queue[tuple[float, float]] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread = None
        self._started = False

    def start(self) -> None:
        """Open the device and launch the reader thread."""
        self._device = self._open_device(self._port)
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._reader_loop, daemon=True,
        )
        self._started = True
        self._thread.start()

    def get_latest(self):
        """Return the most recent (timestamp, value) or None."""
        latest = None
        try:
            while True:
                latest = self._queue.get_nowait()
        except queue.Empty:
            pass
        return latest

    def get_all(self):
        """Drain and return all queued samples."""
        samples = []
        try:
            while True:
                samples.append(self._queue.get_nowait())
        except queue.Empty:
            pass
        return samples

    def stop(self) -> None:
        """Stop the reader thread and close the device."""
        if not self._started:
            return
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._close_device()
        self._started = False

    @property
    def is_running(self) -> bool:
        return self._started and self._thread.is_alive()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    # -- Internal methods (implement for your hardware) --

    def _open_device(self, port):
        """Open a connection to your sensor hardware."""
        raise NotImplementedError

    def _close_device(self):
        """Close the hardware connection."""
        raise NotImplementedError

    def _read_sample(self):
        """Read one sample from the device (blocking)."""
        raise NotImplementedError

    def _reader_loop(self):
        """Background loop: read and enqueue samples."""
        while not self._stop_event.is_set():
            value = self._read_sample()
            self._queue.put((time.time(), value))
```

## Key constraints

1. **Non-blocking main thread** — `get_latest()` and `get_all()` must never block.
2. **Tuple format** — samples are `(timestamp, force)` where timestamp is `time.time()` and force is in Newtons (or your chosen unit — update config accordingly).
3. **Main-thread start for BLE** — if your sensor uses BLE on Windows, `start()` must run on the main thread before importing PsychoPy.
4. **Clean shutdown** — `stop()` must reliably terminate the background thread and release hardware resources.
