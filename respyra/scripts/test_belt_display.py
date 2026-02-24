#!/usr/bin/env python3
"""Test belt + display: full proving-ground experiment.

Connects to the Vernier respiration belt, shows the live breathing
waveform on a PsychoPy window, records force samples and button-press
events to an incremental CSV, and saves everything on exit.

Run from the project root:
    python -m respyra.scripts.test_belt_display
"""

from collections import deque

from respyra.configs.test_experiment import (
    BG_COLOR,
    BELT_CHANNELS,
    BELT_PERIOD_MS,
    CONNECTION,
    DEVICE_TO_OPEN,
    ESCAPE_KEY,
    FULLSCR,
    MONITOR_DISTANCE_CM,
    MONITOR_NAME,
    MONITOR_SIZE_PIX,
    MONITOR_WIDTH_CM,
    OUTPUT_DIR,
    RECORD_DURATION_SEC,
    RESPONSE_KEYS,
    TRACE_BUFFER_SIZE,
    TRACE_COLOR,
    TRACE_RECT,
    TRACE_Y_RANGE,
    UNITS,
)
from respyra.core.breath_belt import BreathBelt, BreathBeltError
from respyra.core.data_logger import DataLogger, create_session_file


# ======================================================================
# Setup
# ======================================================================

def _connect_belt():
    """Connect to the breath belt before PsychoPy is imported.

    On Windows, Bleak's BLE scanner requires the main thread with COM
    in MTA mode.  Importing PsychoPy sets COM to STA, so belt
    connection must happen first.

    Returns the connected BreathBelt, or exits if no device is found.
    """
    belt = None
    print(f"[belt] Searching for device via {CONNECTION.upper()}...")
    try:
        belt = BreathBelt(
            connection=CONNECTION,
            device_to_open=DEVICE_TO_OPEN,
            period_ms=BELT_PERIOD_MS,
            sensors=BELT_CHANNELS,
        )
        belt.start()
        print(f"[belt] Found device via {CONNECTION.upper()}. Connected and streaming.")
    except BreathBeltError as exc:
        print(f"[belt] {CONNECTION.upper()} failed: {exc}")
        if CONNECTION == 'ble':
            print("[belt] Falling back to USB...")
            print("[belt] Searching for device via USB...")
            try:
                belt = BreathBelt(
                    connection='usb',
                    device_to_open=None,
                    period_ms=BELT_PERIOD_MS,
                    sensors=BELT_CHANNELS,
                )
                belt.start()
                print("[belt] Found device via USB. Connected and streaming.")
            except BreathBeltError as usb_exc:
                print(f"[belt] USB also failed: {usb_exc}")
                print("[belt] No device found. Exiting.")
                raise SystemExit(1)
    return belt


def run_experiment():
    # ------------------------------------------------------------------
    # 1. Connect belt BEFORE importing PsychoPy (Windows BLE requires
    #    main thread with COM MTA; PsychoPy import sets COM to STA)
    # ------------------------------------------------------------------
    belt = _connect_belt()

    # ------------------------------------------------------------------
    # 2. Import PsychoPy (safe now that BLE scanning is done)
    # ------------------------------------------------------------------
    from psychopy import core, gui, visual
    from respyra.core.display import SignalTrace, create_monitor, create_window
    from respyra.core.events import check_keys

    # ------------------------------------------------------------------
    # 3. Participant info dialog
    # ------------------------------------------------------------------
    exp_info = {'participant': '', 'session': '001'}
    dlg = gui.DlgFromDict(
        exp_info,
        title='Test Belt Display',
        order=['participant', 'session'],
    )
    if not dlg.OK:
        belt.stop()
        core.quit()
        return

    participant = exp_info['participant']
    session = exp_info['session']

    # ------------------------------------------------------------------
    # 4. Create session file
    # ------------------------------------------------------------------
    filepath = create_session_file(
        participant_id=participant,
        session=session,
        output_dir=OUTPUT_DIR,
    )
    print(f"Data will be saved to: {filepath}")

    # ------------------------------------------------------------------
    # 5. Create monitor and window
    # ------------------------------------------------------------------
    mon = create_monitor(
        name=MONITOR_NAME,
        width_cm=MONITOR_WIDTH_CM,
        distance_cm=MONITOR_DISTANCE_CM,
        size_pix=MONITOR_SIZE_PIX,
    )
    win = create_window(
        fullscr=FULLSCR,
        monitor=mon,
        units=UNITS,
        color=BG_COLOR,
    )

    # ------------------------------------------------------------------
    # 6. Pre-create stimuli, logger, clock (outside frame loop)
    # ------------------------------------------------------------------
    trace = SignalTrace(
        win,
        trace_rect=TRACE_RECT,
        y_range=TRACE_Y_RANGE,
        color=TRACE_COLOR,
    )

    status_text = visual.TextStim(
        win,
        text='',
        color='white',
        height=0.03,
        pos=(0.0, -0.42),
        wrapWidth=1.5,
    )

    # Small marker indicator that flashes on space press
    marker_indicator = visual.Circle(
        win,
        radius=0.02,
        fillColor='red',
        pos=(0.85, 0.42),
    )

    data_logger = DataLogger(filepath)
    exp_clock = core.Clock()
    buffer = deque(maxlen=TRACE_BUFFER_SIZE)
    frame_count = 0
    press_count = 0
    marker_flash_frames = 0  # countdown for how long to show the marker dot

    # ------------------------------------------------------------------
    # Instruction phase
    # ------------------------------------------------------------------
    from respyra.core.display import show_text_and_wait
    show_text_and_wait(
        win,
        text=(
            "You will see your breathing signal in real time.\n\n"
            "Press SPACE whenever you notice a breath.\n\n"
            "Press ESCAPE to end.\n\n"
            "Press SPACE to begin."
        ),
        key_list=['space'],
    )

    # Reset clock after instructions so elapsed time starts at 0
    exp_clock.reset()

    # ==================================================================
    # Main loop (frame-based)
    # ==================================================================
    try:
        running = True
        while running:
            frame_count += 1
            elapsed = exp_clock.getTime()

            # -- Drain new samples from the belt --
            new_samples = belt.get_all()
            for timestamp, force in new_samples:
                buffer.append(force)
                data_logger.log_sample(
                    timestamp=elapsed,
                    frame=frame_count,
                    force_n=force,
                )

            # -- Draw waveform --
            trace.draw(list(buffer))

            # -- Check keys --
            keys = check_keys(
                RESPONSE_KEYS + [ESCAPE_KEY],
                clock=exp_clock,
            )
            for key, rt in keys:
                if key == ESCAPE_KEY:
                    print("Escape pressed -- ending recording.")
                    running = False
                    break
                if key in RESPONSE_KEYS:
                    press_count += 1
                    marker_flash_frames = 10  # show marker for ~10 frames
                    data_logger.log_sample(
                        timestamp=elapsed,
                        frame=frame_count,
                        event_type='keypress',
                        key=key,
                        rt=rt,
                    )
                    print(f"SPACE press #{press_count} at t={rt:.3f}s")

            # -- Draw marker indicator if recently pressed --
            if marker_flash_frames > 0:
                marker_indicator.draw()
                marker_flash_frames -= 1

            # -- Update and draw status text --
            status_text.text = (
                f"Time: {elapsed:.0f}s  |  Presses: {press_count}"
            )
            status_text.draw()

            # -- Flip --
            win.flip()

            # -- Check duration limit --
            if RECORD_DURATION_SEC > 0 and elapsed >= RECORD_DURATION_SEC:
                print(f"Recording duration ({RECORD_DURATION_SEC}s) reached.")
                running = False

    # ==================================================================
    # Cleanup (always runs)
    # ==================================================================
    finally:
        if belt is not None:
            belt.stop()
        data_logger.close()

        # End screen
        try:
            show_text_and_wait(
                win,
                text=(
                    f"Recording complete.\n\n"
                    f"Data saved to:\n{filepath}\n\n"
                    f"Total presses: {press_count}\n\n"
                    f"Press SPACE to exit."
                ),
                key_list=['space'],
            )
        except Exception:
            # If the window is already broken, just print to console
            pass

        print(f"Data saved to: {filepath}")
        print(f"Total button presses: {press_count}")
        print(f"Total frames: {frame_count}")

        win.close()
        core.quit()


if __name__ == '__main__':
    run_experiment()
