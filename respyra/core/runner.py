"""Reusable experiment phases and the default breath tracking runner.

This module decomposes the breath tracking task into composable phase
functions that share state via :class:`ExperimentState`.  The default
runner :func:`run_experiment` composes all phases in order.

**Recipe remixers** call :func:`run_experiment` with an
:class:`~respyra.configs.experiment_config.ExperimentConfig`.

**Power users** import individual phase functions to build custom
experiment flows::

    from respyra.core.runner import (
        connect_belt, setup_display, run_participant_dialog,
        run_range_calibration, run_baseline, run_countdown,
        run_tracking, ExperimentState,
    )
"""

from __future__ import annotations

import colorsys
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from respyra.configs.experiment_config import ExperimentConfig
from respyra.core.breath_belt import BreathBelt, BreathBeltError
from respyra.core.data_logger import DataLogger, create_session_file
from respyra.core.target_generator import TargetGenerator, calibrate_from_baseline

# ====================================================================
# Helpers
# ====================================================================


def apply_gain(buffer, gain: float, center: float) -> list[float]:
    """Return a perturbed copy of *buffer* for display.

    Applies a multiplicative gain around *center*::

        perturbed = center + gain * (force - center)

    When ``gain == 1.0`` returns an unmodified copy.
    """
    if gain == 1.0:
        return list(buffer)
    return [center + gain * (f - center) for f in buffer]


def graded_dot_color(error: float, max_error: float) -> tuple[float, float, float]:
    """Map tracking error to a colour on the green-yellow-red spectrum.

    Returns an RGB tuple in PsychoPy's ``[-1, 1]`` colour space.
    Error 0 maps to green (hue 120 deg), error >= *max_error* maps to
    red (hue 0 deg).  A square-root curve sharpens the falloff so
    small errors already shift noticeably toward yellow.
    """
    t = min(abs(error) / max_error, 1.0)
    t = t**0.5
    hue = (1.0 - t) / 3.0
    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    return (r * 2 - 1, g * 2 - 1, b * 2 - 1)


def _force_to_dot_y(
    force: float,
    y_min: float,
    y_max: float,
    trace_bottom: float,
    trace_top: float,
) -> float:
    """Map a force value to a screen-y position within the trace rect."""
    y_span = y_max - y_min
    normed = 0.5 if y_span == 0 else float(np.clip((force - y_min) / y_span, 0.0, 1.0))
    return trace_bottom + normed * (trace_top - trace_bottom)


def _compute_dot_color(
    current_error: float,
    cfg: ExperimentConfig,
) -> Any:
    """Determine dot colour based on feedback mode and error magnitude."""
    if cfg.dot.feedback_mode == "graded":
        return graded_dot_color(current_error, cfg.dot.graded_max_error_n)
    elif cfg.dot.feedback_mode == "trinary":
        if current_error <= cfg.dot.error_threshold_n:
            return cfg.dot.color_good
        elif current_error <= cfg.dot.error_threshold_mid_n:
            return cfg.dot.color_mid
        else:
            return cfg.dot.color_bad
    else:  # binary
        if current_error <= cfg.dot.error_threshold_n:
            return cfg.dot.color_good
        else:
            return cfg.dot.color_bad


# ====================================================================
# Runtime state
# ====================================================================


@dataclass
class ExperimentState:
    """Mutable state shared across experiment phases.

    Phase functions receive this by reference and mutate it.
    """

    belt: Any  # BreathBelt
    win: Any  # PsychoPy Window
    logger: DataLogger
    clock: Any  # PsychoPy Clock
    buffer: deque
    stimuli: dict  # {"trace", "trace_border", "phase_title", ...}
    # Calibration results — updated by run_range_calibration
    range_center: float = 5.0
    global_amplitude: float = 2.0
    y_min: float = 0.0
    y_max: float = 10.0
    # Accumulated per-trial mean errors
    all_trial_errors: list[float] = field(default_factory=list)
    # Frame counter (persists across phases within a trial)
    frame_count: int = 0


# ====================================================================
# Phase functions
# ====================================================================


def connect_belt(cfg: ExperimentConfig) -> BreathBelt:
    """Connect to the breath belt.

    Must be called **before** importing PsychoPy on Windows (Bleak's
    BLE scanner requires COM in MTA mode; PsychoPy sets COM to STA).

    Attempts the configured connection method first, then falls back
    to USB if BLE fails.
    """
    bc = cfg.belt
    print(f"[belt] Searching for device via {bc.connection.upper()}...")
    try:
        belt = BreathBelt(
            connection=bc.connection,
            device_to_open=bc.device_to_open,
            period_ms=bc.period_ms,
            sensors=bc.channels,
        )
        belt.start()
        print(f"[belt] Found device via {bc.connection.upper()}. Connected and streaming.")
        return belt
    except BreathBeltError as exc:
        print(f"[belt] {bc.connection.upper()} failed: {exc}")
        if bc.connection == "ble":
            print("[belt] Falling back to USB...")
            print("[belt] Searching for device via USB...")
            try:
                belt = BreathBelt(
                    connection="usb",
                    device_to_open=None,
                    period_ms=bc.period_ms,
                    sensors=bc.channels,
                )
                belt.start()
                print("[belt] Found device via USB. Connected and streaming.")
                return belt
            except BreathBeltError as usb_exc:
                print(f"[belt] USB also failed: {usb_exc}")
                print("[belt] No device found. Exiting.")
                raise SystemExit(1) from usb_exc
        raise SystemExit(1) from exc


def setup_display(cfg: ExperimentConfig):
    """Create PsychoPy window and pre-create all stimuli.

    Imports PsychoPy internally (safe after belt connection).

    Returns
    -------
    win : psychopy.visual.Window
    stimuli : dict
        Keys: ``'trace'``, ``'trace_border'``, ``'phase_title'``,
        ``'status_text'``, ``'countdown_text'``, ``'target_dot'``.
    """
    from psychopy import visual

    from respyra.core.display import SignalTrace, create_monitor, create_window

    dc = cfg.display
    tc = cfg.trace

    mon = create_monitor(
        name=dc.monitor_name,
        width_cm=dc.monitor_width_cm,
        distance_cm=dc.monitor_distance_cm,
        size_pix=dc.monitor_size_pix,
    )
    win = create_window(
        fullscr=dc.fullscr,
        monitor=mon,
        units=dc.units,
        color=dc.bg_color,
    )

    trace_left, trace_bottom, trace_right, trace_top = tc.rect
    trace_center_y = (trace_bottom + trace_top) / 2

    stimuli = {
        "trace": SignalTrace(
            win,
            trace_rect=tc.rect,
            y_range=tc.y_range,
            color=tc.color,
        ),
        "trace_border": visual.Rect(
            win,
            width=trace_right - trace_left,
            height=trace_top - trace_bottom,
            pos=((trace_left + trace_right) / 2, (trace_bottom + trace_top) / 2),
            lineColor=tc.border_color,
            lineWidth=1.0,
            fillColor=None,
        ),
        "phase_title": visual.TextStim(
            win,
            text="",
            color="#aaaaaa",
            height=0.05,
            pos=(0.0, 0.45),
            bold=True,
        ),
        "status_text": visual.TextStim(
            win,
            text="",
            color="white",
            height=0.03,
            pos=(0.0, trace_bottom - 0.06),
            wrapWidth=1.5,
        ),
        "countdown_text": visual.TextStim(
            win,
            text="",
            color="white",
            height=0.15,
            pos=(0.0, trace_center_y),
        ),
        "target_dot": visual.Circle(
            win,
            radius=cfg.dot.radius,
            fillColor=cfg.dot.color_good,
            lineColor=cfg.dot.color_good,
        ),
    }

    return win, stimuli


def run_participant_dialog(cfg: ExperimentConfig):
    """Show PsychoPy participant info dialog.

    Returns
    -------
    dict or None
        ``{"participant": str, "session": str}`` if OK was pressed,
        ``None`` if the dialog was cancelled.
    """
    from psychopy import gui

    exp_info = {"participant": "", "session": "001"}
    dlg = gui.DlgFromDict(
        exp_info,
        title=cfg.name,
        order=["participant", "session"],
    )
    if not dlg.OK:
        return None
    return exp_info


def run_range_calibration(state: ExperimentState, cfg: ExperimentConfig) -> bool:
    """Run range calibration with retry loop.

    Mutates *state*: updates ``range_center``, ``global_amplitude``,
    ``y_min``, ``y_max``, and the trace's y-range.

    Returns
    -------
    bool
        ``True`` if calibration was accepted, ``False`` if escaped.
    """
    from respyra.core.display import show_text_and_wait
    from respyra.core.events import check_keys

    s = state
    rc = cfg.range_cal
    escape = cfg.escape_key
    cal_accepted = False

    while not cal_accepted:
        key = show_text_and_wait(
            s.win,
            text=(
                "Breathing Range Calibration\n\n"
                "Breathe normally and comfortably.\n"
                "Try to cover your full natural breathing range\n"
                "without straining.\n\n"
                "This helps us set the right difficulty level.\n\n"
                "Press SPACE when ready."
            ),
            key_list=["space", escape],
        )
        if key == escape:
            print("Escape pressed -- ending experiment.")
            return False

        # Frame loop
        range_cal_forces: list[float] = []
        s.buffer.clear()
        s.stimuli["phase_title"].text = "RANGE CALIBRATION"
        s.clock.reset()
        s.frame_count = 0
        escaped = False

        while s.clock.getTime() < cfg.timing.range_cal_duration_sec:
            s.frame_count += 1
            elapsed = s.clock.getTime()

            new_samples = s.belt.get_all()
            for _ts, force in new_samples:
                s.buffer.append(force)
                range_cal_forces.append(force)
                s.logger.log_row(
                    timestamp=round(elapsed, 4),
                    frame=s.frame_count,
                    force_n=round(force, 4),
                    phase="range_cal",
                    condition="",
                    trial_num=0,
                    feedback_gain=1.0,
                )

            remaining = max(0, cfg.timing.range_cal_duration_sec - elapsed)
            s.stimuli["status_text"].text = f"Breathe normally -- {remaining:.0f}s remaining"

            s.stimuli["trace_border"].draw()
            s.stimuli["trace"].draw(list(s.buffer))
            s.stimuli["phase_title"].draw()
            s.stimuli["status_text"].draw()
            s.win.flip()

            keys = check_keys([escape])
            if keys:
                print("Escape pressed during range calibration.")
                escaped = True
                break

        if escaped:
            return False

        # Compute results
        if not range_cal_forces:
            s.global_amplitude = 2.0
            s.range_center = 5.0
            print("Range calibration: no data collected, using defaults")
            return True

        sorted_forces = sorted(range_cal_forces)
        raw_min = sorted_forces[0]
        raw_max = sorted_forces[-1]

        # Saturation detection
        saturated = any(
            f <= rc.force_saturation_lo or f >= rc.force_saturation_hi for f in range_cal_forces
        )
        sat_warning = ""
        if saturated:
            n_sat = sum(
                1
                for f in range_cal_forces
                if f <= rc.force_saturation_lo or f >= rc.force_saturation_hi
            )
            print(
                f"[cal] WARNING: {n_sat} samples near sensor limits "
                f"({rc.force_saturation_lo}-{rc.force_saturation_hi} N). "
                f"Belt may be too tight."
            )
            sat_warning = "\n\nWARNING: Sensor saturation detected.\nConsider loosening the belt."

        # Percentile clipping
        n = len(sorted_forces)
        lo_idx = int(n * rc.percentile_lo / 100)
        hi_idx = int(n * rc.percentile_hi / 100) - 1
        lo_idx = max(0, min(lo_idx, n - 1))
        hi_idx = max(lo_idx, min(hi_idx, n - 1))
        global_min = sorted_forces[lo_idx]
        global_max = sorted_forces[hi_idx]

        raw_amplitude = (global_max - global_min) / 2.0
        s.global_amplitude = max(raw_amplitude * rc.scale, 0.5)
        s.range_center = (global_max + global_min) / 2.0

        # Set dynamic y_range
        padding = (global_max - global_min) * 0.2
        s.y_min = global_min - padding
        s.y_max = global_max + padding
        s.stimuli["trace"].y_min = s.y_min
        s.stimuli["trace"].y_max = s.y_max

        print(
            f"Range calibration: raw=[{raw_min:.2f}, {raw_max:.2f}] N, "
            f"clipped P{rc.percentile_lo}/{rc.percentile_hi}="
            f"[{global_min:.2f}, {global_max:.2f}] N"
        )
        print(
            f"  center={s.range_center:.2f} N, "
            f"amplitude={s.global_amplitude:.2f} N, "
            f"y_range=[{s.y_min:.2f}, {s.y_max:.2f}]"
        )

        key = show_text_and_wait(
            s.win,
            text=(
                "Calibration Complete\n\n"
                f"Range: {global_min:.1f} - {global_max:.1f} N\n"
                f"Amplitude: {s.global_amplitude:.1f} N\n"
                f"{sat_warning}\n\n"
                "Press SPACE to accept, R to recalibrate."
            ),
            key_list=["space", "r", escape],
        )
        if key == escape:
            return False
        elif key == "r":
            print("[cal] Recalibrating...")
        else:
            cal_accepted = True

    return True


def run_baseline(
    state: ExperimentState,
    cfg: ExperimentConfig,
    condition_name: str,
    trial_num: int,
    total_trials: int,
) -> tuple[list[float], bool]:
    """Run baseline phase (natural breathing for centre calibration).

    Returns
    -------
    baseline_forces : list[float]
    escaped : bool
    """
    from respyra.core.events import check_keys

    s = state
    escape = cfg.escape_key
    baseline_forces: list[float] = []

    s.stimuli["phase_title"].text = f"BASELINE -- Trial {trial_num}/{total_trials}"
    s.clock.reset()

    while s.clock.getTime() < cfg.timing.baseline_duration_sec:
        s.frame_count += 1
        elapsed = s.clock.getTime()

        new_samples = s.belt.get_all()
        for _ts, force in new_samples:
            s.buffer.append(force)
            baseline_forces.append(force)
            s.logger.log_row(
                timestamp=round(elapsed, 4),
                frame=s.frame_count,
                force_n=round(force, 4),
                phase="baseline",
                condition=condition_name,
                trial_num=trial_num,
                feedback_gain=1.0,
            )

        remaining = max(0, cfg.timing.baseline_duration_sec - elapsed)
        s.stimuli["status_text"].text = f"Breathe naturally -- {remaining:.0f}s remaining"

        s.stimuli["trace_border"].draw()
        s.stimuli["trace"].draw(list(s.buffer))
        s.stimuli["phase_title"].draw()
        s.stimuli["status_text"].draw()
        s.win.flip()

        keys = check_keys([escape])
        if keys:
            print("Escape pressed during baseline.")
            return baseline_forces, True

    return baseline_forces, False


def run_countdown(
    state: ExperimentState,
    cfg: ExperimentConfig,
    condition_def,
    condition_name: str,
    trial_num: int,
    total_trials: int,
) -> bool:
    """Run countdown phase (3..2..1) with dot preview blend.

    Returns
    -------
    escaped : bool
    """
    from respyra.core.events import check_keys

    s = state
    escape = cfg.escape_key
    feedback_gain = condition_def.feedback_gain
    trace_left, trace_bottom, trace_right, trace_top = cfg.trace.rect
    countdown_dur = cfg.timing.countdown_duration_sec

    s.stimuli["phase_title"].text = f"GET READY -- Trial {trial_num}/{total_trials}"
    s.clock.reset()

    # Start dot at participant's current position, blend into target
    target_dot = s.stimuli["target_dot"]
    target_dot.fillColor = "#aaaaaa"
    target_dot.lineColor = "#aaaaaa"
    current_force = s.buffer[-1] if s.buffer else s.range_center
    first_freq = condition_def.segments[0].freq_hz

    while s.clock.getTime() < countdown_dur:
        s.frame_count += 1
        elapsed = s.clock.getTime()

        new_samples = s.belt.get_all()
        for _ts, force in new_samples:
            s.buffer.append(force)
            s.logger.log_row(
                timestamp=round(elapsed, 4),
                frame=s.frame_count,
                force_n=round(force, 4),
                phase="countdown",
                condition=condition_name,
                trial_num=trial_num,
                feedback_gain=feedback_gain,
            )

        # Blend from current position into target waveform
        preview_t = elapsed - countdown_dur
        extended_target = s.range_center + s.global_amplitude * np.sin(
            2.0 * np.pi * first_freq * preview_t
        )
        blend = elapsed / countdown_dur
        dot_force = current_force * (1.0 - blend) + extended_target * blend

        dot_y = _force_to_dot_y(dot_force, s.y_min, s.y_max, trace_bottom, trace_top)
        target_dot.pos = (trace_right + cfg.dot.x_offset, dot_y)

        count_num = int(countdown_dur - elapsed) + 1
        count_num = max(1, min(count_num, int(countdown_dur)))
        s.stimuli["countdown_text"].text = str(count_num)
        s.stimuli["status_text"].text = "Get ready -- follow the dot!"

        s.stimuli["trace_border"].draw()
        s.stimuli["trace"].draw(apply_gain(s.buffer, feedback_gain, s.range_center))
        target_dot.draw()
        s.stimuli["countdown_text"].draw()
        s.stimuli["phase_title"].draw()
        s.stimuli["status_text"].draw()
        s.win.flip()

        keys = check_keys([escape])
        if keys:
            print("Escape pressed during countdown.")
            return True

    return False


def run_tracking(
    state: ExperimentState,
    cfg: ExperimentConfig,
    condition_def,
    target_gen: TargetGenerator,
    condition_name: str,
    trial_num: int,
    total_trials: int,
) -> tuple[list[float], bool]:
    """Run the active tracking phase for one trial.

    Returns
    -------
    trial_errors : list[float]
        Absolute compensated errors for each sample.
    escaped : bool
    """
    from respyra.core.events import check_keys

    s = state
    escape = cfg.escape_key
    feedback_gain = condition_def.feedback_gain
    trace_left, trace_bottom, trace_right, trace_top = cfg.trace.rect
    target_dot = s.stimuli["target_dot"]
    trial_errors: list[float] = []

    s.stimuli["phase_title"].text = f"TRACKING -- Trial {trial_num}/{total_trials}"
    s.clock.reset()

    while s.clock.getTime() < cfg.timing.tracking_duration_sec:
        s.frame_count += 1
        tracking_t = s.clock.getTime()

        target_force = target_gen.get_target(tracking_t)

        latest_force = None
        new_samples = s.belt.get_all()
        for _ts, force in new_samples:
            s.buffer.append(force)
            latest_force = force
            error = target_force - force
            visual_force = s.range_center + feedback_gain * (force - s.range_center)
            compensated_error = target_force - visual_force
            trial_errors.append(abs(compensated_error))
            s.logger.log_row(
                timestamp=round(tracking_t, 4),
                frame=s.frame_count,
                force_n=round(force, 4),
                target_force=round(target_force, 4),
                error=round(error, 4),
                compensated_error=round(compensated_error, 4),
                phase="tracking",
                condition=condition_name,
                trial_num=trial_num,
                feedback_gain=feedback_gain,
            )

        dot_y = _force_to_dot_y(target_force, s.y_min, s.y_max, trace_bottom, trace_top)
        target_dot.pos = (trace_right + cfg.dot.x_offset, dot_y)

        if latest_force is not None:
            visual_f = s.range_center + feedback_gain * (latest_force - s.range_center)
            current_error = abs(target_force - visual_f)
            color = _compute_dot_color(current_error, cfg)
            target_dot.fillColor = color
            target_dot.lineColor = color

        remaining = max(0, cfg.timing.tracking_duration_sec - tracking_t)
        s.stimuli["status_text"].text = f"Follow the dot -- {remaining:.0f}s remaining"

        s.stimuli["trace_border"].draw()
        s.stimuli["trace"].draw(apply_gain(s.buffer, feedback_gain, s.range_center))
        target_dot.draw()
        s.stimuli["phase_title"].draw()
        s.stimuli["status_text"].draw()
        s.win.flip()

        keys = check_keys([escape])
        if keys:
            print("Escape pressed during tracking.")
            return trial_errors, True

    return trial_errors, False


def show_trial_feedback(
    state: ExperimentState,
    cfg: ExperimentConfig,
    trial_errors: list[float],
    trial_num: int,
) -> bool:
    """Show post-trial feedback screen.

    Returns ``True`` if escape was pressed.
    """
    from respyra.core.display import show_text_and_wait

    mean_abs_error = sum(trial_errors) / len(trial_errors) if trial_errors else float("nan")
    state.all_trial_errors.append(mean_abs_error)

    key = show_text_and_wait(
        state.win,
        text=(
            f"Trial {trial_num} complete.\n\n"
            f"Mean tracking error: {mean_abs_error:.2f} N\n\n"
            "Press SPACE to continue."
        ),
        key_list=["space", cfg.escape_key],
    )
    return key == cfg.escape_key


def show_end_screen(
    state: ExperimentState,
    cfg: ExperimentConfig,
    filepath: str,
) -> None:
    """Show experiment-complete summary screen."""
    from respyra.core.display import show_text_and_wait

    if state.all_trial_errors:
        overall_mean = sum(state.all_trial_errors) / len(state.all_trial_errors)
    else:
        overall_mean = float("nan")

    show_text_and_wait(
        state.win,
        text=(
            "Experiment complete!\n\n"
            f"Overall mean tracking error: {overall_mean:.2f} N\n\n"
            f"Data saved to:\n{filepath}\n\n"
            "Press SPACE to exit."
        ),
        key_list=["space", cfg.escape_key],
    )


# ====================================================================
# Default runner
# ====================================================================


def run_experiment(cfg: ExperimentConfig | None = None) -> None:
    """Run the standard breath tracking experiment.

    Composes all phases in order: belt connection, display setup,
    participant dialog, range calibration, then the trial loop
    (baseline -> countdown -> tracking -> feedback per trial).

    Power users can call the individual phase functions above to
    build custom experiment flows.

    Parameters
    ----------
    cfg : ExperimentConfig or None
        Experiment configuration.  If ``None``, uses a default
        :class:`ExperimentConfig`.
    """
    if cfg is None:
        from respyra.configs.breath_tracking import CONFIG as _default_cfg

        cfg = _default_cfg

    # 1. Connect belt BEFORE PsychoPy (Windows BLE/COM constraint)
    belt = connect_belt(cfg)

    # 2. Import PsychoPy (safe now)
    from psychopy import core, data

    from respyra.core.display import show_text_and_wait

    # 3. Setup display and stimuli
    win, stimuli = setup_display(cfg)

    filepath = None
    logger = None
    state = None
    error_occurred = False

    try:
        # 4. Participant dialog
        exp_info = run_participant_dialog(cfg)
        if exp_info is None:
            belt.stop()
            win.close()
            core.quit()
            return

        participant = exp_info["participant"]
        session = exp_info["session"]

        # 5. Create session file and logger
        filepath = create_session_file(
            participant_id=participant,
            session=session,
            output_dir=cfg.output_dir,
        )
        print(f"Data will be saved to: {filepath}")

        logger = DataLogger(filepath, columns=cfg.data_columns)
        exp_clock = core.Clock()
        buffer = deque(maxlen=cfg.trace_buffer_size)

        state = ExperimentState(
            belt=belt,
            win=win,
            logger=logger,
            clock=exp_clock,
            buffer=buffer,
            stimuli=stimuli,
            y_min=cfg.trace.y_range[0],
            y_max=cfg.trace.y_range[1],
        )

        # 6. Instructions
        baseline_dur = int(cfg.timing.baseline_duration_sec)
        countdown_dur = int(cfg.timing.countdown_duration_sec)
        tracking_dur = int(cfg.timing.tracking_duration_sec)
        key = show_text_and_wait(
            win,
            text=(
                f"{cfg.name}\n\n"
                "You will see your live breathing signal on screen.\n"
                "A yellow dot will appear at the right edge of the trace.\n\n"
                "Your goal: breathe so your signal follows the dot.\n\n"
                "First, we will calibrate your breathing range.\n"
                "Then, each trial has three phases:\n"
                f"  1. Baseline -- breathe naturally ({baseline_dur} s)\n"
                f"  2. Countdown -- get ready ({countdown_dur} s)\n"
                f"  3. Tracking -- follow the dot ({tracking_dur} s)\n\n"
                "Press SPACE to begin."
            ),
            key_list=["space", cfg.escape_key],
        )
        if key == cfg.escape_key:
            print("Escape pressed -- ending experiment.")
            return

        # 7. Range calibration
        if not run_range_calibration(state, cfg):
            return  # finally handles cleanup

        # 8. Build trial order
        if cfg.trial.build_conditions is not None:
            conditions = cfg.trial.build_conditions(session)
        else:
            conditions = cfg.trial.conditions

        if not conditions:
            print("[error] No conditions defined -- nothing to run.")
            return

        # Map condition names to defs; warn on duplicates with differing params
        condition_map: dict[str, Any] = {}
        for c in conditions:
            if c.name in condition_map and c is not condition_map[c.name]:
                existing = condition_map[c.name]
                if c.feedback_gain != existing.feedback_gain or c.segments != existing.segments:
                    raise ValueError(
                        f"Duplicate condition name '{c.name}' with different parameters. "
                        f"Give each condition a unique name."
                    )
            condition_map[c.name] = c
        trial_list = [{"condition": c.name} for c in conditions]
        trials = data.TrialHandler(
            trialList=trial_list,
            nReps=cfg.trial.n_reps,
            method=cfg.trial.method,
        )

        # 9. Trial loop
        for trial in trials:
            condition_name = trial["condition"]
            condition_def = condition_map[condition_name]
            trial_num = trials.thisN + 1
            total_trials = trials.nTotal

            # Trial info screen
            key = show_text_and_wait(
                win,
                text=(
                    f"Trial {trial_num} of {total_trials}\n\n"
                    f"Condition: {condition_name}\n\n"
                    "Press SPACE when ready."
                ),
                key_list=["space", cfg.escape_key],
            )
            if key == cfg.escape_key:
                print("Escape pressed -- ending experiment.")
                break

            # Fresh buffer per trial
            state.buffer.clear()
            state.frame_count = 0

            # a) Baseline
            baseline_forces, escaped = run_baseline(
                state, cfg, condition_name, trial_num, total_trials
            )
            if escaped:
                break

            # b) Calibrate from baseline (center logged for diagnostics only;
            #    target generation uses the global range calibration values)
            baseline_center, _baseline_amp = calibrate_from_baseline(baseline_forces)
            target_gen = TargetGenerator(condition_def, state.range_center, state.global_amplitude)
            print(
                f"Trial {trial_num}: target center={state.range_center:.2f} N, "
                f"amplitude={state.global_amplitude:.2f} N, "
                f"baseline center={baseline_center:.2f} N, "
                f"feedback_gain={condition_def.feedback_gain}"
            )

            # c) Countdown
            escaped = run_countdown(
                state, cfg, condition_def, condition_name, trial_num, total_trials
            )
            if escaped:
                break

            # d) Tracking
            trial_errors, escaped = run_tracking(
                state,
                cfg,
                condition_def,
                target_gen,
                condition_name,
                trial_num,
                total_trials,
            )
            if escaped:
                break

            # e) Feedback
            if show_trial_feedback(state, cfg, trial_errors, trial_num):
                print("Escape pressed at feedback.")
                break

        else:
            # All trials completed normally
            show_end_screen(state, cfg, filepath)

    except Exception:
        error_occurred = True
        import traceback

        traceback.print_exc()

    finally:
        belt.stop()
        if logger is not None:
            logger.close()

        if filepath is not None:
            print(f"Data saved to: {filepath}")
        if state is not None:
            print(f"Trials completed: {len(state.all_trial_errors)}")
            if state.all_trial_errors:
                overall = sum(state.all_trial_errors) / len(state.all_trial_errors)
                print(f"Overall mean error: {overall:.2f} N")

        win.close()
        if not error_occurred:
            core.quit()
