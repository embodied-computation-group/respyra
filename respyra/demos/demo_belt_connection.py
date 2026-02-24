#!/usr/bin/env python3
"""Demo: basic belt connection and polling.

Terminal-only test -- no PsychoPy required.  Tries BLE first, falls back
to USB if BLE fails, then prints 100 samples (roughly 10 seconds at the
default 100 ms period).

Run from the project root:
    python -m respyra.demos.demo_belt_connection
"""

import time

from respyra.core.breath_belt import BreathBelt, BreathBeltError


def main():
    # ------------------------------------------------------------------
    # Connect: BLE first, USB fallback
    # ------------------------------------------------------------------
    belt = None
    try:
        print("Attempting BLE connection (proximity pairing)...")
        belt = BreathBelt(connection='ble', device_to_open='proximity_pairing')
        belt.start()
        print("BLE connection succeeded.")
    except BreathBeltError as exc:
        print(f"BLE failed: {exc}")
        print("Falling back to USB...")
        try:
            belt = BreathBelt(connection='usb', device_to_open=None)
            belt.start()
            print("USB connection succeeded.")
        except BreathBeltError as usb_exc:
            print(f"USB also failed: {usb_exc}")
            print("No belt connection available. Exiting.")
            return

    # ------------------------------------------------------------------
    # Print device info (accessed via the internal gdx object)
    # ------------------------------------------------------------------
    try:
        if belt._gdx is not None:
            info = belt._gdx.device_info()
            print(f"Device info: {info}")
    except Exception as exc:
        print(f"Could not retrieve device info: {exc}")

    # ------------------------------------------------------------------
    # Poll 100 samples (~10 seconds at 10 Hz)
    # ------------------------------------------------------------------
    try:
        print("\nReading 100 samples (press Ctrl-C to abort)...")
        for i in range(100):
            sample = belt.get_latest()
            if sample is not None:
                timestamp, force = sample
                print(f"  [{i:3d}] t={timestamp:.3f}  force={force:.2f} N")
            else:
                print(f"  [{i:3d}] (no sample)")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        belt.stop()
        print("Belt stopped. Done.")


if __name__ == '__main__':
    main()
