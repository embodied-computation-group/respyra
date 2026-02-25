# Demo: Threaded Belt Reader

**Script:** `respyra/demos/demo_threaded_belt.py`

**What it demonstrates:** The thread + queue pattern used in the full experiment, with `get_all()` for batch sample retrieval.

## How to run

```bash
python -m respyra.demos.demo_threaded_belt
```

## What it does

1. **Connects to the belt** (BLE with USB fallback).
2. **Runs for 10 seconds**, calling `get_all()` every 50 ms to drain the sample queue.
3. **Prints each sample** as it arrives.
4. **Reports a summary** — total samples received, expected count, effective sample rate, and whether any gaps were detected.

## Key code patterns

### Batch retrieval with `get_all()`

```python
batch = belt.get_all()
for timestamp, force in batch:
    process(timestamp, force)
time.sleep(0.05)  # poll every 50 ms
```

Unlike `get_latest()` (which discards old samples), `get_all()` returns **every** sample since the last call. Use this when you need to record all data points (e.g., for CSV logging).

### Sample rate verification

The summary compares expected vs. actual sample counts:

```
--- Summary ---
  Total samples received : 98
  Expected (at 10 Hz for 10s) : ~100
  Effective sample rate  : 9.8 Hz
  No significant gaps detected.
```

A gap of more than 10% triggers a warning — useful for diagnosing Bluetooth interference or CPU contention.
