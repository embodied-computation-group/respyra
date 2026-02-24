#!/usr/bin/env python3
"""Respiratory motor control tracking task.

Participants follow a sinusoidal target dot with their breathing while
the live respiratory waveform is displayed.  The session begins with a
range calibration phase (3 deep breaths) to establish the participant's
full breathing range.  Each trial then has three phases: baseline
(natural breathing for center calibration), countdown, and tracking.

Run from the project root:
    python -m src.scripts.breath_tracking_task
"""

import colorsys
from collections import deque

import numpy as np

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
    DOT_COLOR_MID,
    DOT_FEEDBACK_MODE,
    DOT_GRADED_MAX_ERROR_N,
    DOT_RADIUS,
    DOT_X_OFFSET,
    ERROR_THRESHOLD_MID_N,
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
    RANGE_CAL_DURATION_SEC,
    RANGE_CAL_SCALE,
    TRACE_BORDER_COLOR,
    TRACE_BUFFER_SIZE,
    TRACE_COLOR,
    TRACE_RECT,
    TRACE_Y_RANGE,
    TRACKING_DURATION_SEC,
    UNITS,
)
from src.core.breath_belt import BreathBelt, BreathBeltError
from src.core.data_logger import DataLogger, create_session_file
from src.core.target_generator import TargetGenerator, calibrate_from_baseline


# ======================================================================
# Helpers
# ======================================================================

def _graded_dot_color(error: float, max_error: float) -> tuple[float, float, float]:
    """Map tracking error to a color on the green→yellow→red spectrum.

    Returns an RGB tuple in PsychoPy's [-1, 1] color space.
    Error 0 → green (hue 120°), error >= max_error → red (hue 0°),
    with yellow in the middle.  A square-root curve sharpens the
    falloff so small errors already shift noticeably toward yellow.
    """
    t = min(abs(error) / max_error, 1.0)  # 0 = perfect, 1 = worst
    t = t ** 0.5                           # sharpen: small errors shift faster
    hue = (1.0 - t) / 3.0                 # 0.33 (green) → 0.0 (red)
    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    # Convert [0,1] RGB to PsychoPy [-1,1]
    return (r * 2 - 1, g * 2 - 1, b * 2 - 1)


# ======================================================================
# Main experiment
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
    from psychopy import core, data, gui, visual
    from src.core.display import SignalTrace, create_monitor, create_window, show_text_and_wait
    from src.core.events import check_keys

    # ------------------------------------------------------------------
    # 3. Participant info dialog
    # ------------------------------------------------------------------
    exp_info = {'participant': '', 'session': '001'}
    dlg = gui.DlgFromDict(
        exp_info,
        title='Breath Tracking Task',
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
    # 6. Pre-create ALL stimuli (before any frame loops)
    # ------------------------------------------------------------------
    trace_left, trace_bottom, trace_right, trace_top = TRACE_RECT
    trace_center_y = (trace_bottom + trace_top) / 2

    trace = SignalTrace(
        win,
        trace_rect=TRACE_RECT,
        y_range=TRACE_Y_RANGE,
        color=TRACE_COLOR,
    )

    trace_border = visual.Rect(
        win,
        width=trace_right - trace_left,
        height=trace_top - trace_bottom,
        pos=((trace_left + trace_right) / 2, (trace_bottom + trace_top) / 2),
        lineColor=TRACE_BORDER_COLOR,
        lineWidth=1.0,
        fillColor=None,
    )

    phase_title = visual.TextStim(
        win,
        text='',
        color='#aaaaaa',
        height=0.05,
        pos=(0.0, 0.45),
        bold=True,
    )

    status_text = visual.TextStim(
        win,
        text='',
        color='white',
        height=0.03,
        pos=(0.0, trace_bottom - 0.06),
        wrapWidth=1.5,
    )

    countdown_text = visual.TextStim(
        win,
        text='',
        color='white',
        height=0.15,
        pos=(0.0, trace_center_y),
    )

    target_dot = visual.Circle(
        win,
        radius=DOT_RADIUS,
        fillColor=DOT_COLOR_GOOD,
        lineColor=DOT_COLOR_GOOD,
    )

    # ------------------------------------------------------------------
    # 7. Create DataLogger, clock, signal buffer
    # ------------------------------------------------------------------
    logger = DataLogger(filepath, columns=DATA_COLUMNS)
    exp_clock = core.Clock()
    buffer = deque(maxlen=TRACE_BUFFER_SIZE)

    # ------------------------------------------------------------------
    # 8. Build trial order with TrialHandler
    # ------------------------------------------------------------------
    condition_map = {c.name: c for c in CONDITIONS}
    trial_list = [{'condition': c.name} for c in CONDITIONS]
    trials = data.TrialHandler(
        trialList=trial_list,
        nReps=N_REPS,
        method='random',
    )

    # y_min/y_max for dot positioning -- updated after range calibration
    y_min, y_max = TRACE_Y_RANGE

    # Accumulate per-trial mean errors for the final summary
    all_trial_errors = []

    # ------------------------------------------------------------------
    # 9. Show global instructions
    # ------------------------------------------------------------------
    show_text_and_wait(
        win,
        text=(
            "Respiratory Tracking Task\n\n"
            "You will see your live breathing signal on screen.\n"
            "A yellow dot will appear at the right edge of the trace.\n\n"
            "Your goal: breathe so your signal follows the dot.\n\n"
            "First, we will calibrate your breathing range.\n"
            "Then, each trial has three phases:\n"
            "  1. Baseline -- breathe naturally (10 s)\n"
            "  2. Countdown -- get ready (3 s)\n"
            "  3. Tracking -- follow the dot (30 s)\n\n"
            "Press SPACE to begin."
        ),
        key_list=['space', ESCAPE_KEY],
    )

    # ==================================================================
    # 10. Range calibration phase (once per session)
    # ==================================================================
    try:
        # Show range-cal instruction screen
        key = show_text_and_wait(
            win,
            text=(
                "Breathing Range Calibration\n\n"
                "Take 3 deep breaths:\n"
                "Breathe IN as deeply as you can,\n"
                "then OUT as far as you can.\n\n"
                "This helps us set the right difficulty level.\n\n"
                "Press SPACE when ready."
            ),
            key_list=['space', ESCAPE_KEY],
        )

        escaped = False
        if key == ESCAPE_KEY:
            print("Escape pressed -- ending experiment.")
            escaped = True

        # Range calibration frame loop
        range_cal_forces = []

        if not escaped:
            phase_title.text = "RANGE CALIBRATION"
            exp_clock.reset()
            frame_count = 0

            while exp_clock.getTime() < RANGE_CAL_DURATION_SEC:
                frame_count += 1
                elapsed = exp_clock.getTime()

                # Drain belt samples
                new_samples = belt.get_all()
                for _ts, force in new_samples:
                    buffer.append(force)
                    range_cal_forces.append(force)
                    logger.log_row(
                        timestamp=round(elapsed, 4),
                        frame=frame_count,
                        force_n=round(force, 4),
                        phase='range_cal',
                        condition='',
                        trial_num=0,
                    )

                # Draw
                remaining = max(0, RANGE_CAL_DURATION_SEC - elapsed)
                status_text.text = (
                    f"Breathe deeply -- {remaining:.0f}s remaining"
                )

                trace_border.draw()
                trace.draw(list(buffer))
                phase_title.draw()
                status_text.draw()
                win.flip()

                # Check escape
                keys = check_keys([ESCAPE_KEY])
                if keys:
                    print("Escape pressed during range calibration.")
                    escaped = True
                    break

        # Compute range calibration results
        if range_cal_forces and not escaped:
            global_min = min(range_cal_forces)
            global_max = max(range_cal_forces)
            raw_amplitude = (global_max - global_min) / 2.0
            global_amplitude = max(raw_amplitude * RANGE_CAL_SCALE, 0.5)
            # Use range center so the target stays within the
            # participant's comfortable range.
            range_center = (global_max + global_min) / 2.0

            # Set dynamic y_range for trace and dot positioning
            padding = (global_max - global_min) * 0.2
            y_min = global_min - padding
            y_max = global_max + padding
            trace.y_min = y_min
            trace.y_max = y_max

            print(
                f"Range calibration: min={global_min:.2f} N, "
                f"max={global_max:.2f} N, center={range_center:.2f} N, "
                f"amplitude={global_amplitude:.2f} N"
            )
            print(
                f"Trace y_range set to: [{y_min:.2f}, {y_max:.2f}]"
            )
        else:
            # Fallback if no data was collected
            global_amplitude = 2.0
            range_center = 5.0
            print("Range calibration: no data collected, using defaults")

        if escaped:
            return  # finally block handles cleanup

        # ==============================================================
        # 11. Trial loop
        # ==============================================================
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

            # Start fresh signal buffer per trial so previous-trial data
            # does not bleed into the trace display.
            buffer.clear()
            baseline_forces = []
            frame_count = 0
            escaped = False

            # ----------------------------------------------------------
            # b) Baseline phase (natural breathing for center calibration)
            # ----------------------------------------------------------
            phase_title.text = f"BASELINE -- Trial {trial_num}/{total_trials}"
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
                status_text.text = (
                    f"Breathe naturally -- {remaining:.0f}s remaining"
                )

                trace_border.draw()
                trace.draw(list(buffer))
                phase_title.draw()
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
            # c) Calibrate from baseline (center from baseline, amplitude
            #    from range calibration)
            # ----------------------------------------------------------
            baseline_center, _baseline_amp = calibrate_from_baseline(baseline_forces)
            # Target uses range_center (midpoint of full achievable range)
            # so the sinusoidal target stays within [global_min, global_max].
            # Baseline center is logged for offline drift analysis.
            target_gen = TargetGenerator(condition_def, range_center, global_amplitude)
            print(
                f"Trial {trial_num}: target center={range_center:.2f} N, "
                f"amplitude={global_amplitude:.2f} N, "
                f"baseline center={baseline_center:.2f} N"
            )

            # ----------------------------------------------------------
            # d) Countdown phase (3..2..1)
            # ----------------------------------------------------------
            phase_title.text = f"GET READY -- Trial {trial_num}/{total_trials}"
            exp_clock.reset()

            # Dot starts at the participant's current respiratory position
            # and blends into the target waveform over the countdown.  Uses
            # the first segment's frequency to extend the waveform backwards
            # (avoids cross-segment wrapping artifacts).  Neutral color
            # signals that error is not yet being recorded.
            target_dot.fillColor = '#aaaaaa'
            target_dot.lineColor = '#aaaaaa'
            y_span = y_max - y_min
            current_force = buffer[-1] if buffer else range_center
            first_freq = condition_def.segments[0].freq_hz

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

                # Extend the waveform backwards using the first segment's
                # frequency.  Blend from participant's current position
                # into the target trajectory over the countdown duration.
                preview_t = elapsed - COUNTDOWN_DURATION_SEC  # -3 → 0
                extended_target = range_center + global_amplitude * np.sin(
                    2.0 * np.pi * first_freq * preview_t
                )
                blend = elapsed / COUNTDOWN_DURATION_SEC  # 0 → 1
                dot_force = current_force * (1.0 - blend) + extended_target * blend

                if y_span == 0:
                    normed = 0.5
                else:
                    normed = float(np.clip(
                        (dot_force - y_min) / y_span, 0.0, 1.0,
                    ))
                dot_y = trace_bottom + normed * (trace_top - trace_bottom)
                target_dot.pos = (trace_right + DOT_X_OFFSET, dot_y)

                # Large countdown number (3, 2, 1)
                count_num = int(COUNTDOWN_DURATION_SEC - elapsed) + 1
                count_num = max(1, min(count_num, int(COUNTDOWN_DURATION_SEC)))
                countdown_text.text = str(count_num)

                status_text.text = "Get ready -- follow the dot!"

                trace_border.draw()
                trace.draw(list(buffer))
                target_dot.draw()
                countdown_text.draw()
                phase_title.draw()
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
            phase_title.text = f"TRACKING -- Trial {trial_num}/{total_trials}"
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

                # Dot color feedback
                if latest_force is not None:
                    current_error = abs(target_force - latest_force)
                    if DOT_FEEDBACK_MODE == 'graded':
                        color = _graded_dot_color(current_error, DOT_GRADED_MAX_ERROR_N)
                    elif DOT_FEEDBACK_MODE == 'trinary':
                        if current_error <= ERROR_THRESHOLD_N:
                            color = DOT_COLOR_GOOD
                        elif current_error <= ERROR_THRESHOLD_MID_N:
                            color = DOT_COLOR_MID
                        else:
                            color = DOT_COLOR_BAD
                    else:  # binary (default)
                        color = DOT_COLOR_GOOD if current_error <= ERROR_THRESHOLD_N else DOT_COLOR_BAD
                    target_dot.fillColor = color
                    target_dot.lineColor = color

                remaining = max(0, TRACKING_DURATION_SEC - tracking_t)
                status_text.text = (
                    f"Follow the dot -- {remaining:.0f}s remaining"
                )

                trace_border.draw()
                trace.draw(list(buffer))
                target_dot.draw()
                phase_title.draw()
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
        if belt is not None:
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
