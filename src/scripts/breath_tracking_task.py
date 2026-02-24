#!/usr/bin/env python3
"""Respiratory motor control tracking task.

Participants follow a sinusoidal target dot with their breathing while
the live respiratory waveform is displayed.  Each trial has three phases:
baseline (natural breathing for calibration), countdown, and tracking.

Run from the project root:
    python -m src.scripts.breath_tracking_task
"""

from collections import deque

import numpy as np
from psychopy import core, data, gui, visual

from src.configs.breath_tracking import (
    BASELINE_DURATION_SEC,
    BELT_CHANNELS,
    BELT_PERIOD_MS,
    BG_COLOR,
    CONDITIONS,
    COUNTDOWN_DURATION_SEC,
    DATA_COLUMNS,
    DOT_COLOR_BAD,
    DOT_COLOR_GOOD,
    DOT_RADIUS,
    DOT_X_OFFSET,
    ERROR_THRESHOLD_N,
    ESCAPE_KEY,
    FULLSCR,
    MONITOR_DISTANCE_CM,
    MONITOR_NAME,
    MONITOR_SIZE_PIX,
    MONITOR_WIDTH_CM,
    N_REPS,
    OUTPUT_DIR,
    CONNECTION,
    DEVICE_TO_OPEN,
    TRACE_BUFFER_SIZE,
    TRACE_COLOR,
    TRACE_RECT,
    TRACE_Y_RANGE,
    TRACKING_DURATION_SEC,
    UNITS,
)
from src.core.breath_belt import BreathBelt, BreathBeltError
from src.core.data_logger import DataLogger, create_session_file
from src.core.display import SignalTrace, create_monitor, create_window, show_text_and_wait
from src.core.events import check_keys
from src.core.target_generator import TargetGenerator, calibrate_from_baseline


# ======================================================================
# Main experiment
# ======================================================================

def run_experiment():
    # ------------------------------------------------------------------
    # 1. Participant info dialog
    # ------------------------------------------------------------------
    exp_info = {'participant': '', 'session': '001'}
    dlg = gui.DlgFromDict(
        exp_info,
        title='Breath Tracking Task',
        order=['participant', 'session'],
    )
    if not dlg.OK:
        core.quit()
        return

    participant = exp_info['participant']
    session = exp_info['session']

    # ------------------------------------------------------------------
    # 2. Create session file
    # ------------------------------------------------------------------
    filepath = create_session_file(
        participant_id=participant,
        session=session,
        output_dir=OUTPUT_DIR,
    )
    print(f"Data will be saved to: {filepath}")

    # ------------------------------------------------------------------
    # 3. Create monitor and window
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
    # 4. Connect belt (BLE with USB fallback)
    # ------------------------------------------------------------------
    belt = None
    try:
        print(f"Attempting {CONNECTION} connection...")
        belt = BreathBelt(
            connection=CONNECTION,
            device_to_open=DEVICE_TO_OPEN,
            period_ms=BELT_PERIOD_MS,
            sensors=BELT_CHANNELS,
        )
        belt.start()
        print(f"{CONNECTION.upper()} connection succeeded.")
    except BreathBeltError as exc:
        print(f"{CONNECTION.upper()} failed: {exc}")
        if CONNECTION == 'ble':
            print("Falling back to USB...")
            try:
                belt = BreathBelt(
                    connection='usb',
                    device_to_open=None,
                    period_ms=BELT_PERIOD_MS,
                    sensors=BELT_CHANNELS,
                )
                belt.start()
                print("USB connection succeeded.")
            except BreathBeltError as usb_exc:
                print(f"USB also failed: {usb_exc}")
                win.close()
                core.quit()
                return

    # ------------------------------------------------------------------
    # 5. Pre-create ALL stimuli (before any frame loops)
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

    countdown_text = visual.TextStim(
        win,
        text='',
        color='white',
        height=0.15,
        pos=(0.0, 0.0),
    )

    target_dot = visual.Circle(
        win,
        radius=DOT_RADIUS,
        fillColor=DOT_COLOR_GOOD,
        lineColor=DOT_COLOR_GOOD,
    )

    # ------------------------------------------------------------------
    # 6. Create DataLogger, clock, signal buffer
    # ------------------------------------------------------------------
    logger = DataLogger(filepath, columns=DATA_COLUMNS)
    exp_clock = core.Clock()
    buffer = deque(maxlen=TRACE_BUFFER_SIZE)

    # ------------------------------------------------------------------
    # 7. Build trial order with TrialHandler
    # ------------------------------------------------------------------
    condition_map = {c.name: c for c in CONDITIONS}
    trial_list = [{'condition': c.name} for c in CONDITIONS]
    trials = data.TrialHandler(
        trialList=trial_list,
        nReps=N_REPS,
        method='random',
    )

    # Unpack trace rect bounds for target-dot y-mapping
    trace_left, trace_bottom, trace_right, trace_top = TRACE_RECT
    y_min, y_max = TRACE_Y_RANGE

    # Accumulate per-trial mean errors for the final summary
    all_trial_errors = []

    # ------------------------------------------------------------------
    # 8. Show global instructions
    # ------------------------------------------------------------------
    show_text_and_wait(
        win,
        text=(
            "Respiratory Tracking Task\n\n"
            "You will see your live breathing signal on screen.\n"
            "A yellow dot will appear at the right edge of the trace.\n\n"
            "Your goal: breathe so your signal follows the dot.\n\n"
            "Each trial has three phases:\n"
            "  1. Baseline -- breathe naturally (10 s)\n"
            "  2. Countdown -- get ready (3 s)\n"
            "  3. Tracking -- follow the dot (30 s)\n\n"
            "Press SPACE to begin."
        ),
        key_list=['space', ESCAPE_KEY],
    )

    # ==================================================================
    # 9. Trial loop
    # ==================================================================
    try:
        for trial in trials:
            condition_name = trial['condition']
            condition_def = condition_map[condition_name]
            trial_num = trials.thisN + 1
            total_trials = trials.nTotal

            # ----------------------------------------------------------
            # a) Trial info screen
            # ----------------------------------------------------------
            key = show_text_and_wait(
                win,
                text=(
                    f"Trial {trial_num} of {total_trials}\n\n"
                    f"Condition: {condition_name}\n\n"
                    "Press SPACE when ready."
                ),
                key_list=['space', ESCAPE_KEY],
            )
            if key == ESCAPE_KEY:
                print("Escape pressed -- ending experiment.")
                break

            # Keep the signal buffer continuous within a trial but start
            # fresh so previous-trial data does not bleed into the trace.
            buffer.clear()
            baseline_forces = []
            frame_count = 0
            escaped = False  # tracks escape presses within phase loops

            # ----------------------------------------------------------
            # b) Baseline phase (natural breathing for calibration)
            # ----------------------------------------------------------
            exp_clock.reset()

            while exp_clock.getTime() < BASELINE_DURATION_SEC:
                frame_count += 1
                elapsed = exp_clock.getTime()

                # Drain belt samples
                new_samples = belt.get_all()
                for _ts, force in new_samples:
                    buffer.append(force)
                    baseline_forces.append(force)
                    logger.log_row(
                        timestamp=round(elapsed, 4),
                        frame=frame_count,
                        force_n=round(force, 4),
                        phase='baseline',
                        condition=condition_name,
                        trial_num=trial_num,
                    )

                # Draw
                remaining = max(0, BASELINE_DURATION_SEC - elapsed)
                status_text.text = f"Breathe naturally -- {remaining:.0f}s remaining"
                trace.draw(list(buffer))
                status_text.draw()
                win.flip()

                # Check escape
                keys = check_keys([ESCAPE_KEY])
                if keys:
                    print("Escape pressed during baseline.")
                    escaped = True
                    break

            if escaped:
                break

            # ----------------------------------------------------------
            # c) Calibrate from baseline
            # ----------------------------------------------------------
            center, amplitude = calibrate_from_baseline(baseline_forces)
            target_gen = TargetGenerator(condition_def, center, amplitude)
            print(
                f"Trial {trial_num}: calibrated center={center:.2f} N, "
                f"amplitude={amplitude:.2f} N"
            )

            # ----------------------------------------------------------
            # d) Countdown phase (3..2..1)
            # ----------------------------------------------------------
            exp_clock.reset()

            while exp_clock.getTime() < COUNTDOWN_DURATION_SEC:
                frame_count += 1
                elapsed = exp_clock.getTime()

                # Drain belt samples
                new_samples = belt.get_all()
                for _ts, force in new_samples:
                    buffer.append(force)
                    logger.log_row(
                        timestamp=round(elapsed, 4),
                        frame=frame_count,
                        force_n=round(force, 4),
                        phase='countdown',
                        condition=condition_name,
                        trial_num=trial_num,
                    )

                # Large countdown number (3, 2, 1)
                count_num = int(COUNTDOWN_DURATION_SEC - elapsed) + 1
                count_num = max(1, min(count_num, int(COUNTDOWN_DURATION_SEC)))
                countdown_text.text = str(count_num)

                status_text.text = "Get ready -- follow the dot!"

                trace.draw(list(buffer))
                countdown_text.draw()
                status_text.draw()
                win.flip()

                # Check escape
                keys = check_keys([ESCAPE_KEY])
                if keys:
                    print("Escape pressed during countdown.")
                    escaped = True
                    break

            if escaped:
                break

            # ----------------------------------------------------------
            # e) Tracking phase
            # ----------------------------------------------------------
            exp_clock.reset()
            trial_errors = []

            while exp_clock.getTime() < TRACKING_DURATION_SEC:
                frame_count += 1
                tracking_t = exp_clock.getTime()

                # Compute target for this moment
                target_force = target_gen.get_target(tracking_t)

                # Drain belt samples
                latest_force = None
                new_samples = belt.get_all()
                for _ts, force in new_samples:
                    buffer.append(force)
                    latest_force = force
                    error = target_force - force
                    trial_errors.append(abs(error))
                    logger.log_row(
                        timestamp=round(tracking_t, 4),
                        frame=frame_count,
                        force_n=round(force, 4),
                        target_force=round(target_force, 4),
                        error=round(error, 4),
                        phase='tracking',
                        condition=condition_name,
                        trial_num=trial_num,
                    )

                # Map target force to screen y using the same math
                # as SignalTrace (see src/core/display.py)
                y_span = y_max - y_min
                if y_span == 0:
                    normed = 0.5
                else:
                    normed = (target_force - y_min) / y_span
                    normed = float(np.clip(normed, 0.0, 1.0))
                dot_y = trace_bottom + normed * (trace_top - trace_bottom)

                target_dot.pos = (trace_right + DOT_X_OFFSET, dot_y)

                # Dot color: yellow if tracking well, red if off
                if latest_force is not None:
                    current_error = abs(target_force - latest_force)
                    if current_error <= ERROR_THRESHOLD_N:
                        target_dot.fillColor = DOT_COLOR_GOOD
                        target_dot.lineColor = DOT_COLOR_GOOD
                    else:
                        target_dot.fillColor = DOT_COLOR_BAD
                        target_dot.lineColor = DOT_COLOR_BAD

                remaining = max(0, TRACKING_DURATION_SEC - tracking_t)
                status_text.text = f"Follow the dot -- {remaining:.0f}s remaining"

                trace.draw(list(buffer))
                target_dot.draw()
                status_text.draw()
                win.flip()

                # Check escape
                keys = check_keys([ESCAPE_KEY])
                if keys:
                    print("Escape pressed during tracking.")
                    escaped = True
                    break

            if escaped:
                break

            # ----------------------------------------------------------
            # f) Feedback screen
            # ----------------------------------------------------------
            if trial_errors:
                mean_abs_error = sum(trial_errors) / len(trial_errors)
            else:
                mean_abs_error = float('nan')

            all_trial_errors.append(mean_abs_error)

            key = show_text_and_wait(
                win,
                text=(
                    f"Trial {trial_num} complete.\n\n"
                    f"Mean tracking error: {mean_abs_error:.2f} N\n\n"
                    "Press SPACE to continue."
                ),
                key_list=['space', ESCAPE_KEY],
            )
            if key == ESCAPE_KEY:
                print("Escape pressed at feedback.")
                break

        else:
            # ----------------------------------------------------------
            # g) End screen (only after all trials complete normally)
            # ----------------------------------------------------------
            if all_trial_errors:
                overall_mean = sum(all_trial_errors) / len(all_trial_errors)
            else:
                overall_mean = float('nan')

            show_text_and_wait(
                win,
                text=(
                    "Experiment complete!\n\n"
                    f"Overall mean tracking error: {overall_mean:.2f} N\n\n"
                    f"Data saved to:\n{filepath}\n\n"
                    "Press SPACE to exit."
                ),
                key_list=['space', ESCAPE_KEY],
            )

    # ==================================================================
    # Cleanup (always runs)
    # ==================================================================
    finally:
        belt.stop()
        logger.close()

        print(f"Data saved to: {filepath}")
        print(f"Trials completed: {len(all_trial_errors)}")
        if all_trial_errors:
            overall = sum(all_trial_errors) / len(all_trial_errors)
            print(f"Overall mean error: {overall:.2f} N")

        win.close()
        core.quit()


if __name__ == '__main__':
    run_experiment()
