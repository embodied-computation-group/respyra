#!/usr/bin/env python3
"""Post-session visualization for the breath tracking task.

Generates a 6-panel summary figure from a session CSV file, helping
experimenters evaluate participant performance and verify task operation.

Usage
-----
    python -m respyra.utils.vis.plot_session data/sub-01_ses-001_2026-02-24.csv
    python -m respyra.utils.vis.plot_session data/*.csv --no-show

The figure is saved as ``{csv_stem}_summary.png`` alongside the CSV.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# -- Colors ----------------------------------------------------------------

PHASE_COLORS = {
    "range_cal": "#3d2a2a",  # dark warm (one-time calibration)
    "baseline": "#2a2a3d",  # dark indigo
    "countdown": "#2a3340",  # dark teal
    "tracking": "#1a1a2e",  # near-black (no shading — trace stands out)
}
CONDITION_COLORS = {
    "slow_steady": "#5b9bd5",  # steel blue
    "mixed_rhythm": "#ed7d31",  # warm orange
    "perturbed_slow": "#e05cda",  # magenta
}
CONDITION_SHORT = {
    "slow_steady": "SS",
    "mixed_rhythm": "MR",
    "perturbed_slow": "PS",
}
FORCE_COLOR = "#00e676"  # lime green (matches live trace)
TARGET_COLOR = "#ffa726"  # orange
ERROR_POS_COLOR = "#ef5350"  # red
ZERO_LINE_COLOR = "#666666"


# -- Data loading ----------------------------------------------------------

PHASE_ORDER = {"range_cal": 0, "baseline": 1, "countdown": 2, "tracking": 3}


def load_session(csv_path: str) -> pd.DataFrame:
    """Read a session CSV, coerce column types, and add monotonic session time.

    Parameters
    ----------
    csv_path : str
        Path to a CSV file produced by :class:`respyra.core.data_logger.DataLogger`.

    Returns
    -------
    pd.DataFrame
        DataFrame sorted by ``(trial_num, phase_order, timestamp)`` with an
        additional ``session_time`` column providing monotonic elapsed time
        across phase boundaries.
    """
    df = pd.read_csv(csv_path)

    # Numeric columns (empty strings → NaN)
    for col in ("timestamp", "frame", "force_n", "target_force", "error", "feedback_gain"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "trial_num" in df.columns:
        df["trial_num"] = pd.to_numeric(df["trial_num"], errors="coerce").astype("Int64")

    # Sort chronologically: trial → phase order → timestamp.
    # Frame numbers and timestamps both reset per trial, so we need the
    # phase ordering to reconstruct the correct session sequence.
    df["_phase_ord"] = df["phase"].map(PHASE_ORDER).fillna(9)
    df = df.sort_values(
        ["trial_num", "_phase_ord", "timestamp"],
    ).reset_index(drop=True)
    df = df.drop(columns=["_phase_ord"])

    # Build a monotonic session_time for the full-session trace.
    df["session_time"] = _build_session_time(df)

    return df


def _build_session_time(df: pd.DataFrame) -> pd.Series:
    """Reconstruct monotonic session time from per-phase timestamps.

    The df must already be sorted by (trial_num, phase_order, timestamp).
    """
    session_time = np.zeros(len(df))
    offset = 0.0
    prev_phase = None
    prev_trial = None

    for i in range(len(df)):
        row = df.iloc[i]
        phase = row.get("phase", "")
        trial = row.get("trial_num", np.nan)
        ts = row.get("timestamp", 0.0)
        if pd.isna(ts):
            ts = 0.0

        # Detect phase/trial boundary → bump offset past previous max
        if phase != prev_phase or trial != prev_trial:
            if i > 0:
                offset = session_time[i - 1] + 0.5
            prev_phase = phase
            prev_trial = trial

        session_time[i] = offset + ts

    return pd.Series(session_time, index=df.index)


# -- Per-trial statistics --------------------------------------------------


def compute_trial_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-trial summary statistics from the tracking phase.

    Parameters
    ----------
    df : pd.DataFrame
        Session dataframe as returned by :func:`load_session`.

    Returns
    -------
    pd.DataFrame
        One row per trial with columns: ``trial_num``, ``condition``,
        ``mae`` (mean absolute error in Newtons), ``mae_sd``,
        ``rmse``, and ``n_samples``.  Empty if no tracking data exists.
    """
    tracking = df[df["phase"] == "tracking"].copy()
    if tracking.empty:
        return pd.DataFrame()

    tracking["abs_error"] = tracking["error"].abs()

    stats = (
        tracking.groupby(["trial_num", "condition"])
        .agg(
            mae=("abs_error", "mean"),
            mae_sd=("abs_error", "std"),
            rmse=("error", lambda x: np.sqrt((x**2).mean())),
            n_samples=("error", "count"),
        )
        .reset_index()
    )

    return stats


def compute_baseline_cal(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-trial baseline calibration (center and amplitude).

    Parameters
    ----------
    df : pd.DataFrame
        Session dataframe as returned by :func:`load_session`.

    Returns
    -------
    pd.DataFrame
        One row per trial with columns: ``trial_num``, ``condition``,
        ``force_min``, ``force_max``, ``force_mean``, ``center``
        (midpoint of min/max), and ``amplitude`` (half-range, minimum 0.5 N).
        Empty if no baseline data exists.
    """
    baseline = df[df["phase"] == "baseline"].dropna(subset=["force_n"])
    if baseline.empty:
        return pd.DataFrame()

    cal = (
        baseline.groupby(["trial_num", "condition"])
        .agg(
            force_min=("force_n", "min"),
            force_max=("force_n", "max"),
            force_mean=("force_n", "mean"),
        )
        .reset_index()
    )

    cal["center"] = (cal["force_max"] + cal["force_min"]) / 2
    cal["amplitude"] = ((cal["force_max"] - cal["force_min"]) / 2).clip(lower=0.5)

    return cal


# -- Plotting --------------------------------------------------------------


def plot_session(df: pd.DataFrame, csv_path: str) -> plt.Figure:
    """Create a 6-panel summary figure for one session.

    Panels: (1) full session force trace with target overlay,
    (2) signed tracking error per trial, (3) per-trial MAE bar chart,
    (4) error distribution by condition, (5) baseline calibration stability,
    (6) summary statistics text.

    Parameters
    ----------
    df : pd.DataFrame
        Session dataframe as returned by :func:`load_session`.
    csv_path : str
        Original CSV path, used for the figure title.

    Returns
    -------
    matplotlib.figure.Figure
        The completed figure (not yet saved or shown).
    """
    fig, axes = plt.subplots(3, 2, figsize=(16, 12))
    fig.patch.set_facecolor("#0e0e1a")

    trial_stats = compute_trial_stats(df)
    baseline_cal = compute_baseline_cal(df)
    tracking = df[df["phase"] == "tracking"].copy()

    _plot_full_trace(axes[0, 0], df)
    _plot_error_timeseries(axes[0, 1], tracking)
    _plot_trial_mae_bars(axes[1, 0], trial_stats)
    _plot_error_distribution(axes[1, 1], tracking, trial_stats)
    _plot_baseline_stability(axes[2, 0], baseline_cal)
    _plot_summary_text(axes[2, 1], df, trial_stats, baseline_cal, csv_path)

    fig.suptitle(
        f"Session Summary — {Path(csv_path).stem}",
        color="white",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return fig


def _style_ax(ax, title, xlabel="", ylabel=""):
    """Apply dark-theme styling to an axes."""
    ax.set_facecolor("#1a1a2e")
    ax.set_title(title, color="white", fontsize=11, fontweight="bold", pad=8)
    ax.set_xlabel(xlabel, color="#aaaaaa", fontsize=9)
    ax.set_ylabel(ylabel, color="#aaaaaa", fontsize=9)
    ax.tick_params(colors="#aaaaaa", labelsize=8)
    for spine in ax.spines.values():
        spine.set_color("#333333")
    ax.grid(True, alpha=0.15, color="white")


# -- Panel 1: Full session force trace + target ----------------------------


def _plot_full_trace(ax, df):
    _style_ax(ax, "Full Session Trace", "Session time (s)", "Force (N)")

    trials = sorted(df["trial_num"].dropna().unique())

    # Phase background shading
    for trial_num in trials:
        for phase_name, color in PHASE_COLORS.items():
            mask = (df["trial_num"] == trial_num) & (df["phase"] == phase_name)
            subset = df[mask]
            if subset.empty:
                continue
            t0 = subset["session_time"].iloc[0]
            t1 = subset["session_time"].iloc[-1]
            ax.axvspan(t0, t1, color=color, alpha=0.4)

    # Actual breathing trace
    valid = df.dropna(subset=["force_n"])
    ax.plot(
        valid["session_time"],
        valid["force_n"],
        color=FORCE_COLOR,
        linewidth=0.6,
        alpha=0.85,
        label="Breathing",
    )

    # Target overlay (tracking only)
    target_data = df[(df["phase"] == "tracking") & df["target_force"].notna()]
    if not target_data.empty:
        ax.plot(
            target_data["session_time"],
            target_data["target_force"],
            color=TARGET_COLOR,
            linewidth=1.0,
            linestyle="--",
            alpha=0.8,
            label="Target",
        )

    ax.legend(
        loc="upper right", fontsize=8, facecolor="#1a1a2e", edgecolor="#333333", labelcolor="white"
    )

    # Trial boundary lines + labels (placed after data so ylim is set)
    ymin, ymax = ax.get_ylim()
    for trial_num in trials:
        trial_data = df[df["trial_num"] == trial_num]
        if trial_data.empty:
            continue
        t0 = trial_data["session_time"].iloc[0]
        ax.axvline(t0, color="#555555", linewidth=0.5, linestyle="--")
        cond = (
            trial_data["condition"].dropna().iloc[0]
            if trial_data["condition"].notna().any()
            else ""
        )
        cond_short = CONDITION_SHORT.get(
            cond, cond[:2].upper() if isinstance(cond, str) and cond else "??"
        )
        gain = (
            trial_data["feedback_gain"].iloc[0] if "feedback_gain" in trial_data.columns else 1.0
        )
        gain_str = f" g={gain}" if pd.notna(gain) and gain != 1.0 else ""
        ax.text(
            t0 + 0.3,
            ymax - (ymax - ymin) * 0.03,
            f"T{int(trial_num)} {cond_short}{gain_str}",
            color="#aaaaaa",
            fontsize=7,
            va="top",
            fontweight="bold",
        )


# -- Panel 2: Signed tracking error per trial -----------------------------


def _plot_error_timeseries(ax, tracking):
    _style_ax(ax, "Tracking Error Over Time", "Time in phase (s)", "Error (N)")

    if tracking.empty:
        ax.text(
            0.5,
            0.5,
            "No tracking data",
            transform=ax.transAxes,
            color="#666666",
            ha="center",
            va="center",
            fontsize=12,
        )
        return

    ax.axhline(0, color=ZERO_LINE_COLOR, linewidth=1.0)
    ax.axhline(1.0, color=ERROR_POS_COLOR, linewidth=0.7, linestyle=":", alpha=0.5)
    ax.axhline(-1.0, color=ERROR_POS_COLOR, linewidth=0.7, linestyle=":", alpha=0.5)

    trials = sorted(tracking["trial_num"].dropna().unique())
    cmap = plt.cm.viridis(np.linspace(0.2, 0.9, len(trials)))

    for i, trial_num in enumerate(trials):
        t_data = tracking[tracking["trial_num"] == trial_num]
        cond = t_data["condition"].iloc[0]
        cond_short = CONDITION_SHORT.get(cond, cond[:2].upper())
        # Show gain in label when perturbation is active
        gain = t_data["feedback_gain"].iloc[0] if "feedback_gain" in t_data.columns else 1.0
        gain_str = f" g={gain}" if pd.notna(gain) and gain != 1.0 else ""
        ax.plot(
            t_data["timestamp"],
            t_data["error"],
            color=cmap[i],
            linewidth=0.7,
            alpha=0.8,
            label=f"T{int(trial_num)} ({cond_short}{gain_str})",
        )

    ax.legend(
        loc="upper right",
        fontsize=7,
        facecolor="#1a1a2e",
        edgecolor="#333333",
        labelcolor="white",
        ncol=2,
    )


# -- Panel 3: Per-trial MAE bar chart -------------------------------------


def _plot_trial_mae_bars(ax, trial_stats):
    _style_ax(ax, "Per-Trial Mean Absolute Error", "Trial", "MAE (N)")

    if trial_stats.empty:
        ax.text(
            0.5,
            0.5,
            "No tracking data",
            transform=ax.transAxes,
            color="#666666",
            ha="center",
            va="center",
            fontsize=12,
        )
        return

    trials = trial_stats["trial_num"].values
    mae_vals = trial_stats["mae"].values
    colors = [CONDITION_COLORS.get(c, "#999999") for c in trial_stats["condition"]]

    ax.bar(
        range(len(trials)), mae_vals, color=colors, alpha=0.85, edgecolor="white", linewidth=0.3
    )
    ax.set_xticks(range(len(trials)))
    ax.set_xticklabels([f"T{int(t)}" for t in trials])

    # Overall mean line
    overall_mae = mae_vals.mean()
    ax.axhline(overall_mae, color="white", linewidth=0.8, linestyle="--", alpha=0.6)
    ax.text(
        len(trials) - 0.5,
        overall_mae + 0.02,
        f"mean={overall_mae:.2f}",
        color="white",
        fontsize=7,
        ha="right",
        va="bottom",
    )

    # Legend for conditions
    unique_conds = trial_stats["condition"].unique()
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=CONDITION_COLORS.get(c, "#999")) for c in unique_conds
    ]
    labels = [c.replace("_", " ") for c in unique_conds]
    ax.legend(
        handles,
        labels,
        loc="upper right",
        fontsize=8,
        facecolor="#1a1a2e",
        edgecolor="#333333",
        labelcolor="white",
    )


# -- Panel 4: Error distribution by condition (box plot) -------------------


def _plot_error_distribution(ax, tracking, trial_stats):
    _style_ax(ax, "Error Distribution by Condition", "", "|Error| (N)")

    if tracking.empty:
        ax.text(
            0.5,
            0.5,
            "No tracking data",
            transform=ax.transAxes,
            color="#666666",
            ha="center",
            va="center",
            fontsize=12,
        )
        return

    conditions = sorted(tracking["condition"].dropna().unique())
    box_data = []
    positions = []
    colors = []

    for i, cond in enumerate(conditions):
        cond_errors = tracking[tracking["condition"] == cond]["error"].dropna().abs()
        if not cond_errors.empty:
            box_data.append(cond_errors.values)
            positions.append(i)
            colors.append(CONDITION_COLORS.get(cond, "#999999"))

    if box_data:
        bp = ax.boxplot(
            box_data, positions=positions, widths=0.5, patch_artist=True, showfliers=False
        )

        for patch, color in zip(bp["boxes"], colors, strict=False):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)
            patch.set_edgecolor("white")
        for element in ("whiskers", "caps", "medians"):
            for line in bp[element]:
                line.set_color("white")
                line.set_alpha(0.8)

        # Overlay per-trial means as scatter
        if not trial_stats.empty:
            for i, cond in enumerate(conditions):
                cond_stats = trial_stats[trial_stats["condition"] == cond]
                if not cond_stats.empty:
                    jitter = np.random.default_rng(42).uniform(-0.1, 0.1, len(cond_stats))
                    ax.scatter(
                        i + jitter,
                        cond_stats["mae"],
                        color="white",
                        s=30,
                        zorder=5,
                        edgecolors="none",
                        alpha=0.8,
                        label="Trial MAE" if i == 0 else "",
                    )

    ax.set_xticks(range(len(conditions)))
    ax.set_xticklabels([c.replace("_", " ") for c in conditions], fontsize=9)

    if box_data:
        ax.legend(
            loc="upper right",
            fontsize=8,
            facecolor="#1a1a2e",
            edgecolor="#333333",
            labelcolor="white",
        )


# -- Panel 5: Baseline calibration stability -------------------------------


def _plot_baseline_stability(ax, baseline_cal):
    _style_ax(ax, "Baseline Calibration Stability", "Trial", "Force (N)")

    if baseline_cal.empty:
        ax.text(
            0.5,
            0.5,
            "No baseline data",
            transform=ax.transAxes,
            color="#666666",
            ha="center",
            va="center",
            fontsize=12,
        )
        return

    trials = baseline_cal["trial_num"].values
    centers = baseline_cal["center"].values
    amplitudes = baseline_cal["amplitude"].values
    colors = [CONDITION_COLORS.get(c, "#999") for c in baseline_cal["condition"]]

    # Error bars: center ± amplitude
    for i, (_t, c, a, col) in enumerate(zip(trials, centers, amplitudes, colors, strict=False)):
        ax.errorbar(
            i,
            c,
            yerr=a,
            fmt="o",
            color=col,
            markersize=8,
            capsize=6,
            capthick=1.5,
            elinewidth=1.5,
            markeredgecolor="white",
            markeredgewidth=0.5,
        )

    # Connect centers with a line to show drift
    ax.plot(range(len(trials)), centers, color="white", linewidth=0.8, alpha=0.4, linestyle="--")

    ax.set_xticks(range(len(trials)))
    ax.set_xticklabels([f"T{int(t)}" for t in trials])

    # Legend
    unique_conds = baseline_cal["condition"].unique()
    handles = [
        plt.Line2D(
            [0], [0], marker="o", color=CONDITION_COLORS.get(c, "#999"), linestyle="", markersize=8
        )
        for c in unique_conds
    ]
    labels = [c.replace("_", " ") for c in unique_conds]
    ax.legend(
        handles,
        labels,
        loc="upper right",
        fontsize=8,
        facecolor="#1a1a2e",
        edgecolor="#333333",
        labelcolor="white",
    )


# -- Panel 6: Summary statistics text panel --------------------------------


def _plot_summary_text(ax, df, trial_stats, baseline_cal, csv_path):
    ax.set_facecolor("#1a1a2e")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color("#333333")
    ax.set_title("Summary Statistics", color="white", fontsize=11, fontweight="bold", pad=8)

    tracking = df[df["phase"] == "tracking"]
    lines = []

    # Session info
    lines.append(f"File: {Path(csv_path).name}")
    n_trials = int(df["trial_num"].dropna().nunique())
    lines.append(f"Trials: {n_trials}")
    lines.append(f"Total samples: {len(df)}")
    lines.append(f"Tracking samples: {len(tracking)}")
    lines.append("")

    # Overall performance
    if not trial_stats.empty:
        overall_mae = trial_stats["mae"].mean()
        overall_rmse = trial_stats["rmse"].mean()
        best_idx = trial_stats["mae"].idxmin()
        worst_idx = trial_stats["mae"].idxmax()
        best = trial_stats.loc[best_idx]
        worst = trial_stats.loc[worst_idx]

        lines.append(f"Overall MAE: {overall_mae:.3f} N")
        lines.append(f"Overall RMSE: {overall_rmse:.3f} N")
        lines.append(f"Best trial: T{int(best['trial_num'])} ({best['mae']:.3f} N)")
        lines.append(f"Worst trial: T{int(worst['trial_num'])} ({worst['mae']:.3f} N)")
        lines.append("")

        # Per-condition
        for cond in sorted(trial_stats["condition"].unique()):
            cond_stats = trial_stats[trial_stats["condition"] == cond]
            c_mae = cond_stats["mae"].mean()
            c_sd = cond_stats["mae"].std()
            c_rmse = cond_stats["rmse"].mean()
            label = cond.replace("_", " ")
            # Show gain if present
            cond_tracking = tracking[tracking["condition"] == cond]
            if "feedback_gain" in cond_tracking.columns:
                gain = (
                    cond_tracking["feedback_gain"].dropna().iloc[0]
                    if len(cond_tracking) > 0
                    else 1.0
                )
                gain_str = f" (gain={gain})" if gain != 1.0 else ""
            else:
                gain_str = ""
            lines.append(f"{label}{gain_str}:")
            lines.append(f"  MAE = {c_mae:.3f} +/- {c_sd:.3f} N")
            lines.append(f"  RMSE = {c_rmse:.3f} N")
        lines.append("")

    # Baseline calibration
    if not baseline_cal.empty:
        centers = baseline_cal["center"].values
        amps = baseline_cal["amplitude"].values
        lines.append(
            f"Baseline center: {centers.mean():.2f} N "
            f"(range {centers.min():.2f}-{centers.max():.2f})"
        )
        lines.append(
            f"Baseline amplitude: {amps.mean():.2f} N (range {amps.min():.2f}-{amps.max():.2f})"
        )

    text = "\n".join(lines)
    ax.text(
        0.05,
        0.95,
        text,
        transform=ax.transAxes,
        color="white",
        fontsize=8.5,
        fontfamily="monospace",
        verticalalignment="top",
        linespacing=1.4,
    )


# -- CLI -------------------------------------------------------------------


def main() -> None:
    """CLI entry point: parse arguments and generate summary figures.

    Processes one or more session CSV files, saving each as
    ``{csv_stem}_summary.png`` alongside the original.
    """
    parser = argparse.ArgumentParser(
        description="Generate a 6-panel summary figure from a breath tracking session CSV.",
    )
    parser.add_argument(
        "csv_path",
        nargs="+",
        help="Path(s) to session CSV file(s).",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Save PNG without displaying interactively.",
    )
    args = parser.parse_args()

    for csv_path in args.csv_path:
        if not os.path.isfile(csv_path):
            print(f"File not found: {csv_path}", file=sys.stderr)
            continue

        print(f"Loading {csv_path}...")
        df = load_session(csv_path)

        print(
            f"  {len(df)} rows, "
            f"{df['trial_num'].dropna().nunique()} trials, "
            f"phases: {sorted(df['phase'].dropna().unique())}"
        )

        fig = plot_session(df, csv_path)

        out_path = str(Path(csv_path).with_suffix("")) + "_summary.png"
        fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        print(f"  Saved: {out_path}")

        if not args.no_show:
            plt.show()
        else:
            plt.close(fig)


if __name__ == "__main__":
    main()
