# Demo: Belt Connection

**Script:** `respyra/demos/demo_belt_connection.py`

**What it demonstrates:** Basic belt connectivity and polling — no PsychoPy required.

## How to run

```bash
python -m respyra.demos.demo_belt_connection
```

## What it does

1. **Connects via BLE** using proximity pairing (nearest device). If BLE fails, automatically falls back to USB.
2. **Prints device info** from the internal gdx object.
3. **Reads 100 samples** (~10 seconds at 10 Hz), printing each timestamp and force reading.
4. **Stops the belt** cleanly in a `finally` block.

## Key code patterns

### BLE-first with USB fallback

```python
try:
    belt = BreathBelt(connection='ble', device_to_open='proximity_pairing')
    belt.start()
except BreathBeltError:
    belt = BreathBelt(connection='usb', device_to_open=None)
    belt.start()
```

### Polling with `get_latest()`

```python
sample = belt.get_latest()
if sample is not None:
    timestamp, force = sample
```

`get_latest()` returns the most recent sample and discards any older queued samples. Returns `None` if no new data is available. This is ideal for display updates where only the current value matters.

## Expected output

```
Attempting BLE connection (proximity pairing)...
[belt] Scanning BLE...
[belt] Device found. Configuring sensors [1]...
BLE connection succeeded.
Device info: {'name': 'GDX-RB 081000A1', ...}

Reading 100 samples (press Ctrl-C to abort)...
  [  0] t=1740441234.567  force=4.32 N
  [  1] t=1740441234.667  force=4.28 N
  ...
Belt stopped. Done.
```
