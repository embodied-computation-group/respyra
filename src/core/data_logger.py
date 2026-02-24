"""Incremental CSV data logger for breath-belt experiments.

Writes one row per sample/event, flushing after every write so that data
survives crashes.  No pandas, no heavy abstractions -- just csv.writer
with immediate flush.

Usage
-----
    from src.core.data_logger import create_session_file, DataLogger

    filepath = create_session_file("01")
    with DataLogger(filepath) as log:
        log.log_sample(timestamp=0.016, frame=1, force_n=3.21)
        log.log_sample(timestamp=1.234, frame=74, event_type="keypress",
                       key="space", rt=0.456)
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Optional, Sequence

# ------------------------------------------------------------------ #
#  Default column schema                                              #
# ------------------------------------------------------------------ #
DEFAULT_COLUMNS: list[str] = [
    "timestamp",
    "frame",
    "force_n",
    "event_type",
    "key",
    "rt",
]


# ------------------------------------------------------------------ #
#  Session file helper                                                #
# ------------------------------------------------------------------ #
def create_session_file(
    participant_id: str,
    session: str = "001",
    output_dir: str = "data/",
) -> str:
    """Create an output directory (if needed) and return a unique CSV path.

    Parameters
    ----------
    participant_id : str
        Participant identifier (e.g. ``"01"``).  Will be zero-padded to
        two digits if a bare integer string is supplied.
    session : str, optional
        Session label, default ``"001"``.
    output_dir : str, optional
        Directory for data files, default ``"data/"``.

    Returns
    -------
    str
        Absolute-ish filepath like
        ``data/sub-01_ses-001_2026-02-24_143022.csv``.
        The embedded timestamp prevents accidental overwrites.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Zero-pad a bare digit id: "1" -> "01", but leave "P01" alone.
    if participant_id.isdigit():
        participant_id = participant_id.zfill(2)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = f"sub-{participant_id}_ses-{session}_{timestamp}.csv"
    return os.path.join(output_dir, filename)


# ------------------------------------------------------------------ #
#  DataLogger                                                         #
# ------------------------------------------------------------------ #
class DataLogger:
    """Incremental CSV writer that flushes every row.

    Parameters
    ----------
    filepath : str
        Path to the CSV file (created / overwritten on init).
    columns : list[str] | None
        Header column names.  Falls back to :data:`DEFAULT_COLUMNS` when
        *None*.
    """

    def __init__(
        self,
        filepath: str,
        columns: Optional[Sequence[str]] = None,
    ) -> None:
        self.filepath: str = filepath
        self.columns: list[str] = list(columns) if columns else list(DEFAULT_COLUMNS)

        self._file = open(filepath, "w", newline="", encoding="utf-8")  # noqa: SIM115
        self._writer = csv.writer(self._file)

        # Write the header row immediately.
        self._writer.writerow(self.columns)
        self._file.flush()

    # ---- writing -------------------------------------------------- #

    def log_row(self, **kwargs) -> None:
        """Append a row using keyword arguments matched to column names.

        Any column not present in *kwargs* is written as an empty string.
        This is the generic counterpart to :meth:`log_sample` — use it when
        your experiment needs a custom column schema.
        """
        row = [kwargs.get(col, '') for col in self.columns]
        self._writer.writerow(row)
        self._file.flush()

    def log_sample(
        self,
        timestamp: float,
        frame: int,
        force_n: Optional[float] = None,
        event_type: Optional[str] = None,
        key: Optional[str] = None,
        rt: Optional[float] = None,
    ) -> None:
        """Append a single row and flush to disk.

        Parameters
        ----------
        timestamp : float
            Time in seconds (from experiment clock).
        frame : int
            Frame counter.
        force_n : float | None
            Force reading in newtons from the breath belt.
        event_type : str | None
            Event label, e.g. ``"keypress"``, ``"trial_start"``.
        key : str | None
            Key name if this row records a keypress.
        rt : float | None
            Reaction time in seconds, if applicable.
        """
        row = [timestamp, frame, force_n, event_type, key, rt]
        self._writer.writerow(row)
        self._file.flush()

    # ---- lifecycle ------------------------------------------------ #

    def close(self) -> None:
        """Flush remaining buffer and close the file handle."""
        if not self._file.closed:
            self._file.flush()
            self._file.close()

    # ---- context manager ------------------------------------------ #

    def __enter__(self) -> "DataLogger":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # ---- repr ----------------------------------------------------- #

    def __repr__(self) -> str:
        state = "closed" if self._file.closed else "open"
        return f"DataLogger({self.filepath!r}, {state})"
