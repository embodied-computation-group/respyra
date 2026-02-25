"""Tests for respyra.core.data_logger — file I/O with tmp_path."""

from __future__ import annotations

import csv
import os
from unittest.mock import patch

from respyra.core.data_logger import DEFAULT_COLUMNS, DataLogger, create_session_file

# ================================================================
# create_session_file
# ================================================================


class TestCreateSessionFile:
    def test_creates_directory(self, tmp_path):
        out_dir = str(tmp_path / "new_subdir")
        path = create_session_file("01", output_dir=out_dir)
        assert os.path.isdir(out_dir)
        assert path.startswith(out_dir)

    def test_zero_pads_digit_id(self, tmp_path):
        path = create_session_file("1", output_dir=str(tmp_path))
        assert "sub-01_" in os.path.basename(path)

    def test_preserves_non_digit_id(self, tmp_path):
        path = create_session_file("P01", output_dir=str(tmp_path))
        assert "sub-P01_" in os.path.basename(path)

    def test_default_session(self, tmp_path):
        path = create_session_file("01", output_dir=str(tmp_path))
        assert "_ses-001_" in os.path.basename(path)

    def test_custom_session(self, tmp_path):
        path = create_session_file("01", session="002", output_dir=str(tmp_path))
        assert "_ses-002_" in os.path.basename(path)

    def test_csv_extension(self, tmp_path):
        path = create_session_file("01", output_dir=str(tmp_path))
        assert path.endswith(".csv")

    def test_timestamp_in_filename(self, tmp_path):
        with patch("respyra.core.data_logger.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2026-02-25_120000"
            path = create_session_file("01", output_dir=str(tmp_path))
        assert "2026-02-25_120000" in os.path.basename(path)

    def test_two_digit_id_unchanged(self, tmp_path):
        path = create_session_file("42", output_dir=str(tmp_path))
        assert "sub-42_" in os.path.basename(path)


# ================================================================
# DataLogger
# ================================================================


class TestDataLogger:
    def test_header_written_on_init(self, tmp_path):
        filepath = str(tmp_path / "test.csv")
        logger = DataLogger(filepath)
        logger.close()

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == DEFAULT_COLUMNS

    def test_custom_columns(self, tmp_path):
        filepath = str(tmp_path / "test.csv")
        cols = ["a", "b", "c"]
        logger = DataLogger(filepath, columns=cols)
        logger.close()

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == cols

    def test_log_row_writes_values(self, tmp_path):
        filepath = str(tmp_path / "test.csv")
        cols = ["x", "y", "z"]
        with DataLogger(filepath, columns=cols) as logger:
            logger.log_row(x=1, y=2, z=3)

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            row = next(reader)
        assert row == ["1", "2", "3"]

    def test_log_row_missing_columns_are_empty(self, tmp_path):
        filepath = str(tmp_path / "test.csv")
        cols = ["x", "y", "z"]
        with DataLogger(filepath, columns=cols) as logger:
            logger.log_row(x=1)

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)
        assert row == ["1", "", ""]

    def test_log_row_extra_keys_ignored(self, tmp_path):
        filepath = str(tmp_path / "test.csv")
        cols = ["x"]
        with DataLogger(filepath, columns=cols) as logger:
            logger.log_row(x=1, extra_key="ignored")

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)
        assert row == ["1"]

    def test_log_sample_writes_all_fields(self, tmp_path):
        filepath = str(tmp_path / "test.csv")
        with DataLogger(filepath) as logger:
            logger.log_sample(timestamp=1.0, frame=1, force_n=3.5, event_type="sample")

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)
        assert row[0] == "1.0"
        assert row[1] == "1"
        assert row[2] == "3.5"
        assert row[3] == "sample"

    def test_log_sample_none_values(self, tmp_path):
        filepath = str(tmp_path / "test.csv")
        with DataLogger(filepath) as logger:
            logger.log_sample(timestamp=0.5, frame=1)

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)
        # None values written as empty strings
        assert row[2] == ""  # force_n
        assert row[3] == ""  # event_type

    def test_flush_after_each_write(self, tmp_path):
        filepath = str(tmp_path / "test.csv")
        logger = DataLogger(filepath)
        logger.log_sample(timestamp=1.0, frame=1, force_n=5.0)
        # Read file while still open — should have data due to flush
        with open(filepath, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 2  # header + 1 data row
        logger.close()

    def test_context_manager_closes_file(self, tmp_path):
        filepath = str(tmp_path / "test.csv")
        with DataLogger(filepath) as logger:
            pass
        assert logger._file.closed

    def test_double_close_is_safe(self, tmp_path):
        filepath = str(tmp_path / "test.csv")
        logger = DataLogger(filepath)
        logger.close()
        logger.close()  # should not raise

    def test_repr_open(self, tmp_path):
        filepath = str(tmp_path / "test.csv")
        logger = DataLogger(filepath)
        assert "open" in repr(logger)
        logger.close()

    def test_repr_closed(self, tmp_path):
        filepath = str(tmp_path / "test.csv")
        logger = DataLogger(filepath)
        logger.close()
        assert "closed" in repr(logger)

    def test_multiple_rows(self, tmp_path):
        filepath = str(tmp_path / "test.csv")
        with DataLogger(filepath) as logger:
            for i in range(10):
                logger.log_sample(timestamp=float(i), frame=i, force_n=float(i) * 0.5)

        with open(filepath, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 11  # header + 10 data rows
