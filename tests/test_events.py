"""Tests for respyra.core.events — mock psychopy.event, test record_event."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from respyra.core.events import check_keys, record_event, wait_for_key

# ================================================================
# record_event (pure function — no mocking needed)
# ================================================================


class TestRecordEvent:
    def test_appends_dict_to_list(self):
        log = []
        record_event(log, "trial_start", 1.5)
        assert len(log) == 1
        assert log[0]["event_type"] == "trial_start"
        assert log[0]["timestamp"] == 1.5

    def test_extra_data_merged(self):
        log = []
        record_event(log, "response", 2.0, key="space", rt=0.45)
        assert log[0]["key"] == "space"
        assert log[0]["rt"] == 0.45

    def test_multiple_events_accumulated(self):
        log = []
        record_event(log, "start", 0.0)
        record_event(log, "end", 10.0)
        assert len(log) == 2
        assert log[0]["event_type"] == "start"
        assert log[1]["event_type"] == "end"

    def test_preserves_existing_entries(self):
        log = [{"event_type": "existing", "timestamp": 0.0}]
        record_event(log, "new", 1.0)
        assert len(log) == 2
        assert log[0]["event_type"] == "existing"


# ================================================================
# check_keys (mocked psychopy.event)
# ================================================================


class TestCheckKeys:
    def test_no_keys_returns_empty(self):
        with patch("respyra.core.events.event") as mock_event:
            mock_event.getKeys.return_value = []
            result = check_keys()
        assert result == []

    def test_returns_list_of_tuples(self):
        with patch("respyra.core.events.event") as mock_event:
            mock_event.getKeys.return_value = [["space", 1.23], ["a", 1.45]]
            result = check_keys()
        assert result == [("space", 1.23), ("a", 1.45)]

    def test_passes_key_list(self):
        with patch("respyra.core.events.event") as mock_event:
            mock_event.getKeys.return_value = []
            check_keys(key_list=["space", "escape"])
            mock_event.getKeys.assert_called_with(keyList=["space", "escape"], timeStamped=True)

    def test_passes_clock(self):
        mock_clock = MagicMock()
        with patch("respyra.core.events.event") as mock_event:
            mock_event.getKeys.return_value = []
            check_keys(clock=mock_clock)
            mock_event.getKeys.assert_called_with(keyList=None, timeStamped=mock_clock)


# ================================================================
# wait_for_key (mocked psychopy.event)
# ================================================================


class TestWaitForKey:
    def test_returns_tuple_on_keypress(self):
        with patch("respyra.core.events.event") as mock_event:
            mock_event.waitKeys.return_value = [["space", 0.5]]
            result = wait_for_key()
        assert result == ("space", 0.5)

    def test_returns_none_on_timeout(self):
        with patch("respyra.core.events.event") as mock_event:
            mock_event.waitKeys.return_value = None
            result = wait_for_key(max_wait=1.0)
        assert result is None

    def test_passes_max_wait(self):
        with patch("respyra.core.events.event") as mock_event:
            mock_event.waitKeys.return_value = None
            wait_for_key(max_wait=5.0)
            mock_event.waitKeys.assert_called_with(maxWait=5.0, keyList=None, timeStamped=True)
