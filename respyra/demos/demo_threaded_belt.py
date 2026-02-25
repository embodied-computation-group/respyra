#!/usr/bin/env python3
"""Demo: threaded belt reader using get_all() to drain the queue.

Terminal-only test -- no PsychoPy required.  Demonstrates the
thread+queue pattern: the background thread pushes samples and the
main thread drains them with get_all() at ~50 ms intervals.

Run from the project root:
    python -m respyra.demos.demo_threaded_belt
"""

import time

from respyra.core.breath_belt import BreathBelt, BreathBeltError

DURATION_SEC = 10  # total run time
POLL_INTERVAL = 0.05  # seconds between get_all() calls
EXPECTED_PERIOD = 0.1  # belt default period (100 ms = 10 Hz)


def connect_belt():
    """Try BLE first, fall back to USB.  Returns a started BreathBelt."""
    try:
        print("Attempting BLE connection (proximity pairing)...")
        belt = BreathBelt(connection="ble", device_to_open="proximity_pairing")
        belt.start()
        print("BLE connection succeeded.")
        return belt
    except BreathBeltError as exc:
        print(f"BLE failed: {exc}")

    print("Falling back to USB...")
    belt = BreathBelt(connection="usb", device_to_open=None)
    belt.start()
    print("USB connection succeeded.")
    return belt


def main():
    belt = connect_belt()

    total_samples = 0
    expected_samples = int(DURATION_SEC / EXPECTED_PERIOD)
    first_timestamp = None
    last_timestamp = None

    print(
        f"\nDraining queue for {DURATION_SEC} seconds "
        f"(polling every {POLL_INTERVAL * 1000:.0f} ms)...\n"
    )

    start_time = time.time()

    try:
        while (time.time() - start_time) < DURATION_SEC:
            batch = belt.get_all()
            for timestamp, force in batch:
                total_samples += 1
                if first_timestamp is None:
                    first_timestamp = timestamp
                last_timestamp = timestamp
                print(f"  #{total_samples:4d}  t={timestamp:.3f}  force={force:.2f} N")
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        belt.stop()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n--- Summary ---")
    print(f"  Total samples received : {total_samples}")
    print(
        f"  Expected (at {1 / EXPECTED_PERIOD:.0f} Hz for {DURATION_SEC}s) : ~{expected_samples}"
    )

    if first_timestamp is not None and last_timestamp is not None:
        actual_span = last_timestamp - first_timestamp
        if total_samples > 1:
            actual_rate = (total_samples - 1) / actual_span
            print(f"  Actual span            : {actual_span:.3f} s")
            print(f"  Effective sample rate  : {actual_rate:.1f} Hz")

    if total_samples < expected_samples * 0.9:
        gap_pct = (1 - total_samples / expected_samples) * 100
        print(f"  WARNING: {gap_pct:.1f}% fewer samples than expected -- possible data gaps.")
    else:
        print("  No significant gaps detected.")

    print("Done.")


if __name__ == "__main__":
    main()
