# Troubleshooting

## Belt not found

**Symptom:** `BreathBeltError: No Go Direct device found via ble`

**Solutions:**
- Ensure the belt is powered on (LED blinking)
- Move the belt closer to the computer's Bluetooth antenna
- Try USB as a fallback: set `CONNECTION = 'usb'` in the config or connect the belt with the included USB cable
- On Windows, ensure no other application (e.g., Vernier Graphical Analysis) is connected to the belt
- Restart the belt by pressing and holding the power button

## BLE fails on Windows

**Symptom:** BLE scanning hangs or raises a COM error

**Cause:** PsychoPy's graphics backend initialises COM in STA mode, which conflicts with Bleak's BLE scanner (requires MTA).

**Solution:** respyra handles this automatically by connecting the belt before importing PsychoPy. If you write custom scripts, ensure `belt.start()` is called **before** any `import psychopy` statement. See `respyra/scripts/breath_tracking_task.py` for the correct pattern.

## Sensor saturation

**Symptom:** During range calibration, you see "Sensor Saturation Detected"

**Cause:** Force readings are hitting the sensor limits (0 N floor or ~40 N ceiling). The belt is likely too tight.

**Solution:** Loosen the belt slightly so comfortable deep breaths stay within the ~2–30 N range. Re-run the range calibration.

## PsychoPy version issues

**Symptom:** Import errors or unexpected behavior after updating PsychoPy

**Solution:** respyra requires PsychoPy ≥ 2026.1.0 on Python 3.10. PsychoPy does not support Python 3.11+. Create a dedicated virtual environment:

```bash
py -3.10 -m venv .venv
.venv\Scripts\activate
pip install respyra
```

## Dropped samples

**Symptom:** Fewer belt samples than expected (reported by `demo_threaded_belt`)

**Possible causes:**
- Bluetooth interference — move other BLE devices away
- CPU load — close unnecessary applications during experiments
- `period_ms` set below 10 ms — the minimum is 10 ms (100 Hz)

**Diagnosis:** Run `python -m respyra.demos.demo_threaded_belt` and check the summary report. At 10 Hz over 10 seconds you should see ~100 samples. A gap of more than 10% triggers a warning.

## Frame drops in PsychoPy

**Symptom:** Visual stuttering during the experiment

**Solutions:**
- Set `FULLSCR = True` in the config (enables VSync)
- Close other graphical applications
- Disable desktop compositing on Linux
- Check that monitor refresh rate matches expectations with `win.recordFrameIntervals = True`

## Linux USB permissions

**Symptom:** `Permission denied` when connecting via USB on Linux

**Solution:** Add a udev rule:

```bash
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="08f7", MODE="0666"' | \
    sudo tee /etc/udev/rules.d/99-godirect.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Then unplug and replug the belt.

## Data file not created

**Symptom:** No CSV file in `data/`

**Solutions:**
- Check that the `data/` directory exists (it's created automatically, but verify permissions)
- Ensure the experiment wasn't terminated before any data was written
- Check the console output for the filepath — it's printed at startup
