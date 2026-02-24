# Vernier Go Direct Respiration Belt (GDX-RB) — Python Interface Guide

> Context document for coding agents interfacing with the Vernier Go Direct Respiration Belt using Python.

## Hardware Overview

The **Go Direct Respiration Belt (GDX-RB)** is a chest-strap force sensor that measures breathing effort via belt tension. It connects over **USB** or **Bluetooth Low Energy (BLE)**.

### Data Channels

| Channel | Name             | Unit | Description                                   |
|---------|------------------|------|-----------------------------------------------|
| 1       | Force            | N    | Raw belt tension (0–50 N). Primary signal.    |
| 2       | Respiration Rate | BPM  | Derived breaths/min from Force channel.       |
| 3       | Steps            | —    | Pedometer step count.                         |
| 4       | Step Rate        | SPM  | Derived steps/min.                            |

**Channel 1 (Force) is the workhorse.** It gives the raw respiration waveform — each inhale produces a peak, each exhale a trough. Use this for real-time processing, peak detection, or custom rate calculation.

**Channel 2 (Respiration Rate) has a warmup delay.** It returns `NaN` for approximately the first 30 seconds while it builds an internal baseline. After that, it updates roughly every 10 seconds. Do not rely on it for immediate or high-resolution rate tracking.

---

## Python Stack

### `godirect` — the pip-installable library

```bash
pip3 install godirect
```

This is the core driver. It handles USB (via `hidapi`) and BLE (via `bleak`) communication. Verify with `pip3 show godirect`.

### `gdx` — the convenience wrapper (not on PyPI)

The `gdx` module is a simplified wrapper around `godirect`. It lives in the [godirect-examples](https://github.com/VernierST/godirect-examples) repo under `python/gdx/`. It is **not** installed via pip — you must copy the `gdx/` folder into your project directory (or onto `sys.path`).

The wrapper provides the entire sensor lifecycle in six calls:

```
open → select_sensors → start → read (loop) → stop → close
```

---

## API Reference (`gdx` module)

### `gdx.open(connection, device_to_open=None)`

Opens a device connection.

| Parameter         | Type   | Description |
|-------------------|--------|-------------|
| `connection`      | `str`  | `'usb'` or `'ble'` |
| `device_to_open`  | `str`  | Optional. Device name (e.g. `"GDX-RB 081000A1"`), comma-separated names for multiple devices, or `"proximity_pairing"` for closest BLE device. If omitted, prompts interactively (or auto-connects if only one USB device is found). |

```python
gdx.open(connection='usb')
gdx.open(connection='ble', device_to_open='proximity_pairing')
gdx.open(connection='ble', device_to_open='GDX-RB 081000A1')
```

### `gdx.select_sensors(sensors=None)`

Enables channels for data collection.

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `sensors` | `list` | 1D list for one device: `[1]`, `[1,2]`. 2D list for multiple devices: `[[1,2],[1]]`. If omitted, prompts interactively. |

```python
gdx.select_sensors([1])       # Force only
gdx.select_sensors([1, 2])    # Force + Respiration Rate
```

### `gdx.start(period=None)`

Begins data collection.

| Parameter | Type  | Description |
|-----------|-------|-------------|
| `period`  | `int` | Sampling interval in milliseconds. If omitted, prompts interactively. |

**Minimum reliable period is 10 ms (100 Hz).** Faster rates may cause data loss or timing issues. For respiration, 100–1000 ms (1–10 Hz) is typical.

```python
gdx.start(100)    # 10 Hz — good default for respiration waveform
gdx.start(1000)   # 1 Hz  — low-rate monitoring
```

### `gdx.read()`

Returns a single sample from all enabled sensors.

- **Returns:** `list[float]` — one value per enabled channel, in channel order. Returns `None` if the device disconnects or the buffer is empty.
- **Blocking:** This call blocks until the next sample is available based on the configured period.

```python
measurements = gdx.read()  # e.g. [12.34, 15.0] for channels [1, 2]
```

### `gdx.stop()`

Halts data collection. The device stays connected — you can call `start()` again.

### `gdx.close()`

Disconnects the device and shuts down the `godirect` backend. No further `gdx` calls are valid after this.

### Introspection Methods

| Method                      | Returns                                         | Example output                                    |
|-----------------------------|------------------------------------------------|--------------------------------------------------|
| `gdx.device_info()`        | `[name, description, battery%, charger, rssi]` | `['GDX-RB 081000A1', 'Respiration Belt', 95, 'Idle', -45]` |
| `gdx.sensor_info()`        | 2D list of all available sensors with units and incompatibilities | See source |
| `gdx.enabled_sensor_info()`| 1D list of `"description (units)"` strings     | `['Force (N)', 'Respiration Rate (breaths/min)']` |

---

## Code Examples

### Minimal USB Acquisition

```python
from gdx import gdx

dev = gdx.gdx()
dev.open(connection='usb')
dev.select_sensors([1])          # Force channel only
dev.start(100)                   # 10 Hz

try:
    for _ in range(100):         # 10 seconds of data
        sample = dev.read()
        if sample is None:
            break
        print(sample[0])         # Force in Newtons
finally:
    dev.stop()
    dev.close()
```

### BLE with Proximity Pairing

```python
from gdx import gdx

dev = gdx.gdx()
dev.open(connection='ble', device_to_open='proximity_pairing')
dev.select_sensors([1, 2])
dev.start(500)                   # 2 Hz

headers = dev.enabled_sensor_info()
print(headers)                   # ['Force (N)', 'Respiration Rate (breaths/min)']

try:
    while True:
        row = dev.read()
        if row is None:
            break
        force, resp_rate = row[0], row[1]
        print(f"Force: {force:.2f} N | Rate: {resp_rate} BPM")
except KeyboardInterrupt:
    pass
finally:
    dev.stop()
    dev.close()
```

### Export to CSV

```python
import csv
from gdx import gdx

dev = gdx.gdx()
dev.open(connection='usb')
dev.select_sensors([1])
dev.start(200)                   # 5 Hz

with open('breath_data.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(dev.enabled_sensor_info())

    try:
        for _ in range(300):     # 60 seconds at 5 Hz
            row = dev.read()
            if row is None:
                break
            writer.writerow(row)
    finally:
        dev.stop()
        dev.close()
```

---

## Platform Setup Notes

### Linux (including Raspberry Pi)

```bash
sudo apt install libusb-1.0-0 libudev-dev
```

Copy the udev rules file for USB access:

```bash
# Download from: github.com/VernierST/godirect-examples/python/vstlibusb.rules
sudo cp vstlibusb.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
# Replug the device
```

### Windows

- BLE requires Windows 10+.
- If `pip3 install godirect` fails with compiler errors, install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).

### macOS

No special setup. USB and BLE work natively.

### All Platforms — BLE

- **Do not manually pair** the device in OS Bluetooth settings. The `godirect` library handles pairing internally. Manual pairing causes connection failures.
- For Bluegiga BLED112 dongle (alternative BLE adapter): `pip3 install vernierpygatt` and use `use_ble_bg=True` in the `GoDirect` constructor.

---

## Agent Implementation Checklist

1. **Install:** `pip3 install godirect` + copy `gdx/` folder to project.
2. **Always set `select_sensors()` and `start()` arguments explicitly** to avoid interactive prompts that block automated scripts.
3. **Default to channel 1 (Force)** for raw respiration data. Only add channel 2 if you need the device's own rate estimate (and can tolerate 30s warmup + NaN values).
4. **Use period >= 10 ms.** For respiration waveforms, 100 ms (10 Hz) gives good resolution. For simple monitoring, 500–1000 ms is fine.
5. **Always wrap in try/finally** calling `stop()` then `close()`. Failure to close leaves the device in a streaming state requiring physical power cycle.
6. **`read()` returns a flat list** ordered by enabled channel number. Index 0 = first enabled channel.

---

## Reference Links

- [godirect on PyPI](https://pypi.org/project/godirect/)
- [godirect-examples repo](https://github.com/VernierST/godirect-examples)
- [Getting Started Guide](https://vernierst.github.io/godirect-examples/python/)
- [GDX Channel Numbers (TIL 16315)](https://www.vernier.com/til/16315)
- [Python Troubleshooting (TIL 16133)](https://www.vernier.com/til/16133)
- [Go Direct + Python FAQ (TIL 19229)](https://www.vernier.com/til/19229)
- Support: support@vernier.com
