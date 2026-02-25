"""Shared analysis functions for the validation study paper.

Provides data loading, respiratory metric extraction, breath phase labeling,
and per-trial statistics computation used by the paper figure scripts.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

# -- Phase ordering (for session time reconstruction) ----------------------

PHASE_ORDER = {"range_cal": 0, "baseline": 1, "countdown": 2, "tracking": 3}


# -- Data loading ----------------------------------------------------------


def load_sessions(paths: list[str]) -> pd.DataFrame:
    """Load and concatenate session CSVs, adding a ``session`` column."""
    frames = []
    for p in sorted(paths):
        df = pd.read_csv(p)
        for col in (
            "timestamp",
            "frame",
            "force_n",
            "target_force",
            "error",
            "compensated_error",
            "feedback_gain",
        ):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "trial_num" in df.columns:
            df["trial_num"] = pd.to_numeric(df["trial_num"], errors="coerce").astype("Int64")
        stem = Path(p).stem
        ses_part = [x for x in stem.split("_") if x.startswith("ses-")]
        ses_num = int(ses_part[0].replace("ses-", "")) if ses_part else len(frames) + 1
        df["session"] = ses_num
        frames.append(df)
        print(f"  Loaded {p} (session {ses_num}, {len(df)} rows)")
    return pd.concat(frames, ignore_index=True)


def build_session_time(df: pd.DataFrame) -> pd.Series:
    """Reconstruct monotonic elapsed time from per-phase timestamps.

    Sorts internally by ``(trial_num, phase_order, timestamp)``, computes
    cumulative elapsed time, then maps back to the caller's index.
    """
    work = df[["phase", "trial_num", "timestamp"]].copy()
    work["_phase_ord"] = work["phase"].map(PHASE_ORDER).fillna(9)
    sorted_idx = work.sort_values(["trial_num", "_phase_ord", "timestamp"]).index

    session_time = np.zeros(len(sorted_idx))
    offset = 0.0
    prev_phase = None
    prev_trial = None

    for pos, orig_i in enumerate(sorted_idx):
        row = work.loc[orig_i]
        phase = row["phase"]
        trial = row["trial_num"]
        ts = row["timestamp"] if not pd.isna(row["timestamp"]) else 0.0
        if phase != prev_phase or trial != prev_trial:
            if pos > 0:
                offset = session_time[pos - 1] + 0.5
            prev_phase = phase
            prev_trial = trial
        session_time[pos] = offset + ts

    # Map computed times back to the original index order
    result = pd.Series(index=df.index, dtype=float)
    result.loc[sorted_idx] = session_time
    return result


# -- Respiratory metrics ---------------------------------------------------


def detect_breath_peaks(
    force: np.ndarray,
    sampling_rate: float = 10.0,
    min_cycle_sec: float = 8.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Detect inspiration peaks and expiration troughs in a force signal.

    Parameters
    ----------
    force : array
        Raw ``force_n`` values.
    sampling_rate : float
        Samples per second (default 10.0).
    min_cycle_sec : float
        Minimum expected breath cycle duration in seconds (default 8.0,
        conservative for 0.1 Hz = 10 s target cycles).

    Returns
    -------
    peaks, troughs : tuple of int arrays
        Indices of inspiration peaks (local maxima) and expiration troughs
        (local minima).
    """
    force = np.asarray(force, dtype=float)
    min_dist = int(min_cycle_sec * sampling_rate * 0.7)
    # Prominence threshold: reject peaks smaller than 10% of the signal range
    signal_range = force.max() - force.min()
    prom = max(0.05, signal_range * 0.1)
    peaks, _ = find_peaks(force, distance=min_dist, prominence=prom)
    troughs, _ = find_peaks(-force, distance=min_dist, prominence=prom)
    return peaks, troughs


def compute_respiratory_metrics(
    force: np.ndarray,
    sampling_rate: float = 10.0,
) -> dict:
    """Compute breathing rate, depth, and regularity from a force signal.

    Returns
    -------
    dict
        ``breathing_rate_bpm`` : mean breaths per minute
        ``breathing_depth_n``  : mean peak-to-trough amplitude (N)
        ``n_complete_cycles``  : detected complete cycles
        ``cycle_duration_cv``  : coefficient of variation of cycle durations
    """
    peaks, troughs = detect_breath_peaks(force, sampling_rate)

    result = {
        "breathing_rate_bpm": np.nan,
        "breathing_depth_n": np.nan,
        "n_complete_cycles": 0,
        "cycle_duration_cv": np.nan,
    }

    if len(peaks) < 2:
        return result

    # Breathing rate from peak-to-peak intervals
    peak_intervals = np.diff(peaks) / sampling_rate  # seconds
    cycle_durations = peak_intervals
    result["breathing_rate_bpm"] = 60.0 / cycle_durations.mean()
    result["n_complete_cycles"] = len(cycle_durations)
    if cycle_durations.mean() > 0:
        result["cycle_duration_cv"] = cycle_durations.std() / cycle_durations.mean()

    # Breathing depth: pair each peak with the nearest preceding trough
    depths = []
    for pk in peaks:
        preceding = troughs[troughs < pk]
        if len(preceding) > 0:
            depths.append(force[pk] - force[preceding[-1]])
    if depths:
        result["breathing_depth_n"] = float(np.mean(depths))

    return result


# -- Breath phase labeling ------------------------------------------------


def label_breath_phase(target_force: np.ndarray) -> np.ndarray:
    """Label each sample as ``'inspiration'`` or ``'expiration'``.

    Uses the derivative of the target sinusoid: positive (target rising) =
    inspiration, negative (target falling) = expiration.
    """
    gradient = np.gradient(np.asarray(target_force, dtype=float))
    return np.where(gradient > 0, "inspiration", "expiration")


# -- Trial statistics ------------------------------------------------------


def compute_trial_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-trial MAE, respiratory metrics, and breath-phase errors.

    Operates on tracking-phase data only. Returns one row per
    ``(session, trial_num)``.
    """
    tracking = df[df["phase"] == "tracking"].copy()
    tracking["abs_error"] = tracking["error"].abs()
    tracking["abs_comp_error"] = tracking["compensated_error"].abs()
    tracking["breath_phase"] = label_breath_phase(tracking["target_force"].values)

    rows = []
    for (sess, tnum, cond, gain), grp in tracking.groupby(
        ["session", "trial_num", "condition", "feedback_gain"]
    ):
        force = grp["force_n"].dropna().values
        resp = compute_respiratory_metrics(force)

        insp = grp[grp["breath_phase"] == "inspiration"]
        exp = grp[grp["breath_phase"] == "expiration"]

        rows.append(
            {
                "session": sess,
                "trial_num": tnum,
                "condition": cond,
                "feedback_gain": gain,
                "raw_mae": grp["abs_error"].mean(),
                "raw_sd": grp["abs_error"].std(),
                "comp_mae": grp["abs_comp_error"].mean(),
                "comp_sd": grp["abs_comp_error"].std(),
                "insp_raw_mae": insp["abs_error"].mean() if len(insp) else np.nan,
                "insp_comp_mae": insp["abs_comp_error"].mean() if len(insp) else np.nan,
                "exp_raw_mae": exp["abs_error"].mean() if len(exp) else np.nan,
                "exp_comp_mae": exp["abs_comp_error"].mean() if len(exp) else np.nan,
                "breathing_rate_bpm": resp["breathing_rate_bpm"],
                "breathing_depth_n": resp["breathing_depth_n"],
                "n_complete_cycles": resp["n_complete_cycles"],
                "cycle_duration_cv": resp["cycle_duration_cv"],
                "n_samples": len(grp),
            }
        )

    trials = pd.DataFrame(rows)

    # Within-block trial index (1-N within each condition per session)
    for sess in trials["session"].unique():
        for cond in trials["condition"].unique():
            mask = (trials["session"] == sess) & (trials["condition"] == cond)
            trials.loc[mask, "block_trial"] = range(1, mask.sum() + 1)

    return trials


def compute_session_stats(df: pd.DataFrame, trials: pd.DataFrame) -> pd.DataFrame:
    """Compute per-session summary statistics for Table 1.

    Parameters
    ----------
    df : pd.DataFrame
        Full session data (all phases, all sessions).
    trials : pd.DataFrame
        Per-trial stats from :func:`compute_trial_stats`.
    """
    rows = []
    for sess, st in trials.groupby("session"):
        sess_df = df[df["session"] == sess]

        # Duration from last timestamp in last phase of last trial
        sess_sorted = sess_df.copy()
        sess_sorted["_phase_ord"] = sess_sorted["phase"].map(PHASE_ORDER).fillna(9)
        sess_sorted = sess_sorted.sort_values(["trial_num", "_phase_ord", "timestamp"])
        # Sum max timestamp per (trial, phase) group + inter-phase gaps
        phase_durations = (
            sess_sorted.groupby(["trial_num", "phase"])["timestamp"].max().reset_index()
        )
        total_sec = phase_durations["timestamp"].sum()
        duration_min = total_sec / 60.0

        slow = st[st["condition"] == "slow_steady"]
        pert = st[st["condition"] == "perturbed_slow"]

        rows.append(
            {
                "session": sess,
                "n_trials": len(st),
                "duration_min": duration_min,
                "breathing_rate_bpm_mean": st["breathing_rate_bpm"].mean(),
                "breathing_rate_bpm_sd": st["breathing_rate_bpm"].std(),
                "breathing_depth_n_mean": st["breathing_depth_n"].mean(),
                "breathing_depth_n_sd": st["breathing_depth_n"].std(),
                "n_cycles": int(st["n_complete_cycles"].sum()),
                "cycle_cv_mean": st["cycle_duration_cv"].mean(),
                "slow_raw_mae": slow["raw_mae"].mean(),
                "slow_raw_sd": slow["raw_mae"].std(),
                "slow_comp_mae": slow["comp_mae"].mean(),
                "slow_comp_sd": slow["comp_mae"].std(),
                "pert_raw_mae": pert["raw_mae"].mean(),
                "pert_raw_sd": pert["raw_mae"].std(),
                "pert_comp_mae": pert["comp_mae"].mean(),
                "pert_comp_sd": pert["comp_mae"].std(),
            }
        )

    return pd.DataFrame(rows)
