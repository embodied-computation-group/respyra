"""Visualization scripts for the validation study data.

Usage:
    python paper/plot_validation.py data/sub-m_ses-001*.csv data/sub-m_ses-002*.csv
    python paper/plot_validation.py data/sub-m_ses-*.csv

Generates:
    data/adaptation_within_block.png   — per-session within-block learning curves
    data/adaptation_cross_session.png  — cross-session transfer and savings
    data/split_half_reliability.png    — trial-level split-half (odd/even samples)
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")


# ------------------------------------------------------------------
# Data loading
# ------------------------------------------------------------------


def load_sessions(paths: list[str]) -> pd.DataFrame:
    """Load and concatenate session CSVs, adding session column."""
    frames = []
    for p in sorted(paths):
        df = pd.read_csv(p)
        # Extract session number from filename (sub-X_ses-NNN_...)
        stem = Path(p).stem
        ses_part = [x for x in stem.split("_") if x.startswith("ses-")]
        ses_num = int(ses_part[0].replace("ses-", "")) if ses_part else len(frames) + 1
        df["session"] = ses_num
        frames.append(df)
        print(f"  Loaded {p} (session {ses_num}, {len(df)} rows)")
    return pd.concat(frames, ignore_index=True)


def compute_trial_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-trial MAE from tracking phase data."""
    tracking = df[df["phase"] == "tracking"]
    trials = (
        tracking.groupby(["session", "trial_num", "condition", "feedback_gain"])
        .agg(
            raw_mae=("error", lambda x: x.abs().mean()),
            comp_mae=("compensated_error", lambda x: x.abs().mean()),
            n_samples=("error", "count"),
        )
        .reset_index()
    )
    # Add within-block trial index (1-N within each condition per session)
    for sess in trials["session"].unique():
        for cond in trials["condition"].unique():
            mask = (trials["session"] == sess) & (trials["condition"] == cond)
            trials.loc[mask, "block_trial"] = range(1, mask.sum() + 1)
    return trials


# ------------------------------------------------------------------
# Plot 1: Within-block adaptation
# ------------------------------------------------------------------


def plot_within_block(trials: pd.DataFrame, output: str) -> None:
    """Per-session within-block learning curves (raw + compensated)."""
    sessions = sorted(trials["session"].unique())
    n_sess = len(sessions)

    fig, axes = plt.subplots(n_sess, 2, figsize=(13, 5 * n_sess), sharey="row", squeeze=False)

    for row, sess in enumerate(sessions):
        st = trials[(trials["session"] == sess) & (trials["condition"] == "slow_steady")]
        pt = trials[(trials["session"] == sess) & (trials["condition"] == "perturbed_slow")]
        n_trials = max(len(st), len(pt))

        for col, (metric, title_suffix) in enumerate(
            [("raw_mae", "Raw Error"), ("comp_mae", "Compensated Error")]
        ):
            ax = axes[row, col]
            if len(st) > 0:
                ax.plot(
                    st["block_trial"], st[metric], "o-",
                    color="#2196F3", label="slow_steady", linewidth=2, markersize=8,
                )
            if len(pt) > 0:
                ax.plot(
                    pt["block_trial"], pt[metric], "s-",
                    color="#E91E63", label="perturbed (2x)", linewidth=2, markersize=8,
                )
            ax.set_title(f"Session {sess} — {title_suffix}", fontsize=12)
            ax.legend(fontsize=9)
            ax.set_xticks(range(1, n_trials + 1))
            ax.set_xlim(0.5, n_trials + 0.5)
            ax.grid(alpha=0.3)
            if col == 0:
                ax.set_ylabel("Mean Absolute Error (N)", fontsize=11)

    for ax in axes[-1]:
        ax.set_xlabel("Trial within block", fontsize=11)

    fig.suptitle("Within-Block Adaptation", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output, dpi=150, bbox_inches="tight")
    print(f"  Saved: {output}")
    plt.close(fig)


# ------------------------------------------------------------------
# Plot 2: Cross-session transfer
# ------------------------------------------------------------------


def plot_cross_session(trials: pd.DataFrame, output: str) -> None:
    """Cross-session savings, asymptotic performance, and full timeline."""
    sessions = sorted(trials["session"].unique())
    n_sess = len(sessions)
    max_block = int(trials["block_trial"].max())

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Panel A: First trial of each block across sessions
    ax = axes[0]
    first = trials[trials["block_trial"] == 1]
    x = np.arange(n_sess)
    w = 0.35
    for i, (cond, color, label) in enumerate([
        ("slow_steady", "#2196F3", "slow_steady"),
        ("perturbed_slow", "#E91E63", "perturbed"),
    ]):
        vals = [
            first[(first["session"] == s) & (first["condition"] == cond)]["comp_mae"].values
            for s in sessions
        ]
        vals = [v[0] if len(v) > 0 else 0 for v in vals]
        ax.bar(x + i * w - w / 2, vals, width=w, color=color, label=label)
    ax.set_xticks(x)
    ax.set_xticklabels([f"Session {s}" for s in sessions])
    ax.set_ylabel("Compensated MAE (N)", fontsize=11)
    ax.set_title("First Trial of Each Block\n(savings)", fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, axis="y")

    # Panel B: Last trial of each block across sessions
    ax = axes[1]
    last = trials[trials["block_trial"] == max_block]
    for i, (cond, color, label) in enumerate([
        ("slow_steady", "#2196F3", "slow_steady"),
        ("perturbed_slow", "#E91E63", "perturbed"),
    ]):
        vals = [
            last[(last["session"] == s) & (last["condition"] == cond)]["comp_mae"].values
            for s in sessions
        ]
        vals = [v[0] if len(v) > 0 else 0 for v in vals]
        ax.bar(x + i * w - w / 2, vals, width=w, color=color, label=label)
    ax.set_xticks(x)
    ax.set_xticklabels([f"Session {s}" for s in sessions])
    ax.set_ylabel("Compensated MAE (N)", fontsize=11)
    ax.set_title("Last Trial of Each Block\n(asymptotic performance)", fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, axis="y")

    # Panel C: Full timeline across all sessions
    ax = axes[2]
    all_trials = trials.sort_values(["session", "trial_num"]).reset_index(drop=True)
    all_trials["global_trial"] = range(1, len(all_trials) + 1)

    for cond, color, marker, label in [
        ("slow_steady", "#2196F3", "o", "slow_steady"),
        ("perturbed_slow", "#E91E63", "s", "perturbed"),
    ]:
        sub = all_trials[all_trials["condition"] == cond]
        ax.plot(
            sub["global_trial"], sub["comp_mae"], f"{marker}-",
            color=color, label=label, linewidth=2, markersize=7,
        )

    # Session break lines
    trials_per_session = all_trials.groupby("session")["global_trial"].max().values
    for boundary in trials_per_session[:-1]:
        ax.axvline(boundary + 0.5, color="gray", linestyle="--", alpha=0.5)

    ax.set_xlabel("Global trial number", fontsize=11)
    ax.set_ylabel("Compensated MAE (N)", fontsize=11)
    ax.set_title("Full Timeline\n(cross-session transfer)", fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    fig.suptitle("Cross-Session Motor Adaptation", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output, dpi=150, bbox_inches="tight")
    print(f"  Saved: {output}")
    plt.close(fig)


# ------------------------------------------------------------------
# Plot 3: Split-half reliability (odd vs even trials)
# ------------------------------------------------------------------


def plot_split_half(trials: pd.DataFrame, output: str) -> None:
    """Split-half reliability: pair odd trials (1,3,5) with even trials (2,4,6).

    Within each session×condition block, trial 1 is paired with trial 2,
    trial 3 with trial 4, trial 5 with trial 6. Each pair becomes one
    point on the scatter. This gives 3 points per block, so with
    N sessions × 2 conditions = 6N total points.
    """
    def spearman_brown(r):
        return 2 * r / (1 + abs(r))

    pairs = []
    for (sess, cond), block in trials.groupby(["session", "condition"]):
        block = block.sort_values("block_trial")
        odd = block[block["block_trial"].isin([1, 3, 5])].reset_index(drop=True)
        even = block[block["block_trial"].isin([2, 4, 6])].reset_index(drop=True)
        for i in range(min(len(odd), len(even))):
            pairs.append({
                "session": sess,
                "condition": cond,
                "raw_odd": odd.iloc[i]["raw_mae"],
                "raw_even": even.iloc[i]["raw_mae"],
                "comp_odd": odd.iloc[i]["comp_mae"],
                "comp_even": even.iloc[i]["comp_mae"],
            })

    sh = pd.DataFrame(pairs)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, odd_col, even_col, title in [
        (axes[0], "raw_odd", "raw_even", "Raw Error"),
        (axes[1], "comp_odd", "comp_even", "Compensated Error"),
    ]:
        for cond, color, marker, label in [
            ("slow_steady", "#2196F3", "o", "slow_steady"),
            ("perturbed_slow", "#E91E63", "s", "perturbed (2x)"),
        ]:
            sub = sh[sh["condition"] == cond]
            ax.scatter(
                sub[odd_col], sub[even_col],
                c=color, marker=marker, s=80, label=label, zorder=3,
            )

        all_vals = pd.concat([sh[odd_col], sh[even_col]])
        lim = (0, all_vals.max() * 1.15)
        ax.plot(lim, lim, "k--", alpha=0.3, label="identity")
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        ax.set_xlabel("Odd-trial MAE (N)", fontsize=11)
        ax.set_ylabel("Even-trial MAE (N)", fontsize=11)

        r = sh[odd_col].corr(sh[even_col])
        sb = spearman_brown(r)
        ax.set_title(f"{title}\nr = {r:.3f}, Spearman-Brown = {sb:.3f}", fontsize=12)
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
        ax.set_aspect("equal")

    fig.suptitle(
        "Split-Half Reliability (Odd vs Even Trials)",
        fontsize=14, fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(output, dpi=150, bbox_inches="tight")
    print(f"  Saved: {output}")
    plt.close(fig)


# ------------------------------------------------------------------
# Plot 4: Asymptotic split-half reliability
# ------------------------------------------------------------------


def plot_asymptotic_split_half(trials: pd.DataFrame, output: str) -> None:
    """Split-half using only the last 4 trials of each block (post-learning plateau).

    Trials 3-6 within each block are used. Odd (3,5) vs even (4,6) are paired.
    This removes the early-learning transient and tests reliability of the
    stable performance measure.
    """
    def spearman_brown(r):
        return 2 * r / (1 + abs(r))

    # Keep only trials 3-6 (asymptotic phase)
    asymp = trials[trials["block_trial"] >= 3].copy()

    pairs = []
    for (sess, cond), block in asymp.groupby(["session", "condition"]):
        block = block.sort_values("block_trial")
        odd = block[block["block_trial"].isin([3, 5])].reset_index(drop=True)
        even = block[block["block_trial"].isin([4, 6])].reset_index(drop=True)
        for i in range(min(len(odd), len(even))):
            pairs.append({
                "session": sess,
                "condition": cond,
                "raw_odd": odd.iloc[i]["raw_mae"],
                "raw_even": even.iloc[i]["raw_mae"],
                "comp_odd": odd.iloc[i]["comp_mae"],
                "comp_even": even.iloc[i]["comp_mae"],
            })

    sh = pd.DataFrame(pairs)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, odd_col, even_col, title in [
        (axes[0], "raw_odd", "raw_even", "Raw Error"),
        (axes[1], "comp_odd", "comp_even", "Compensated Error"),
    ]:
        for cond, color, marker, label in [
            ("slow_steady", "#2196F3", "o", "slow_steady"),
            ("perturbed_slow", "#E91E63", "s", "perturbed (2x)"),
        ]:
            sub = sh[sh["condition"] == cond]
            ax.scatter(
                sub[odd_col], sub[even_col],
                c=color, marker=marker, s=80, label=label, zorder=3,
            )

        all_vals = pd.concat([sh[odd_col], sh[even_col]])
        lim = (0, all_vals.max() * 1.15)
        ax.plot(lim, lim, "k--", alpha=0.3, label="identity")
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        ax.set_xlabel("Odd-trial MAE (N)", fontsize=11)
        ax.set_ylabel("Even-trial MAE (N)", fontsize=11)

        r = sh[odd_col].corr(sh[even_col])
        sb = spearman_brown(r)
        ax.set_title(f"{title}\nr = {r:.3f}, Spearman-Brown = {sb:.3f}", fontsize=12)
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
        ax.set_aspect("equal")

    fig.suptitle(
        "Asymptotic Split-Half Reliability (Trials 3-6 Only)",
        fontsize=14, fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(output, dpi=150, bbox_inches="tight")
    print(f"  Saved: {output}")
    plt.close(fig)


# ------------------------------------------------------------------
# Plot 5: Test-retest of adaptation effect
# ------------------------------------------------------------------


def plot_adaptation_retest(trials: pd.DataFrame, output: str) -> None:
    """Test-retest reliability of the adaptation effect across sessions.

    Adaptation effect = first trial MAE - last trial MAE within each block.
    Plotted per condition across sessions. With enough sessions this shows
    whether the learning signal is stable.
    """
    sessions = sorted(trials["session"].unique())

    # Compute adaptation effect per session × condition
    effects = []
    for (sess, cond), block in trials.groupby(["session", "condition"]):
        block = block.sort_values("block_trial")
        first = block[block["block_trial"] == 1].iloc[0]
        last = block[block["block_trial"] == block["block_trial"].max()].iloc[0]
        effects.append({
            "session": sess,
            "condition": cond,
            "raw_first": first["raw_mae"],
            "raw_last": last["raw_mae"],
            "raw_adapt": first["raw_mae"] - last["raw_mae"],
            "comp_first": first["comp_mae"],
            "comp_last": last["comp_mae"],
            "comp_adapt": first["comp_mae"] - last["comp_mae"],
            "comp_block_mean": block["comp_mae"].mean(),
        })

    eff = pd.DataFrame(effects)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Panel A: Block mean MAE across sessions (test-retest of level)
    ax = axes[0]
    for cond, color, marker, label in [
        ("slow_steady", "#2196F3", "o", "slow_steady"),
        ("perturbed_slow", "#E91E63", "s", "perturbed (2x)"),
    ]:
        sub = eff[eff["condition"] == cond].sort_values("session")
        ax.plot(
            sub["session"], sub["comp_block_mean"], f"{marker}-",
            color=color, label=label, linewidth=2, markersize=8,
        )
    ax.set_xlabel("Session", fontsize=11)
    ax.set_ylabel("Block Mean Compensated MAE (N)", fontsize=11)
    ax.set_title("Block-Level Performance\nacross Sessions", fontsize=12)
    ax.set_xticks(sessions)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # Panel B: Adaptation magnitude across sessions
    ax = axes[1]
    for cond, color, marker, label in [
        ("slow_steady", "#2196F3", "o", "slow_steady"),
        ("perturbed_slow", "#E91E63", "s", "perturbed (2x)"),
    ]:
        sub = eff[eff["condition"] == cond].sort_values("session")
        ax.plot(
            sub["session"], sub["comp_adapt"], f"{marker}-",
            color=color, label=label, linewidth=2, markersize=8,
        )
    ax.axhline(0, color="gray", linestyle=":", alpha=0.5)
    ax.set_xlabel("Session", fontsize=11)
    ax.set_ylabel("Adaptation (first - last MAE, N)", fontsize=11)
    ax.set_title("Within-Block Adaptation\nMagnitude across Sessions", fontsize=12)
    ax.set_xticks(sessions)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # Panel C: First-trial MAE across sessions (savings)
    ax = axes[2]
    for cond, color, marker, label in [
        ("slow_steady", "#2196F3", "o", "slow_steady"),
        ("perturbed_slow", "#E91E63", "s", "perturbed (2x)"),
    ]:
        sub = eff[eff["condition"] == cond].sort_values("session")
        ax.plot(
            sub["session"], sub["comp_first"], f"{marker}-",
            color=color, label=label, linewidth=2, markersize=8,
        )
    ax.set_xlabel("Session", fontsize=11)
    ax.set_ylabel("First-Trial Compensated MAE (N)", fontsize=11)
    ax.set_title("First-Trial Performance\n(between-session savings)", fontsize=12)
    ax.set_xticks(sessions)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    fig.suptitle("Test-Retest: Adaptation Effect across Sessions", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output, dpi=150, bbox_inches="tight")
    print(f"  Saved: {output}")
    plt.close(fig)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------


def main():
    if len(sys.argv) < 2:
        print("Usage: python paper/plot_validation.py data/*.csv")
        sys.exit(1)

    import glob

    paths = []
    for arg in sys.argv[1:]:
        paths.extend(glob.glob(arg))

    if not paths:
        print("No CSV files found.")
        sys.exit(1)

    print(f"Loading {len(paths)} session file(s)...")
    df = load_sessions(paths)
    trials = compute_trial_stats(df)

    print(f"\nTotal: {len(trials)} trials across {trials['session'].nunique()} sessions")
    print()

    plot_within_block(trials, "data/adaptation_within_block.png")
    plot_cross_session(trials, "data/adaptation_cross_session.png")
    plot_split_half(trials, "data/split_half_reliability.png")
    plot_asymptotic_split_half(trials, "data/asymptotic_split_half.png")
    plot_adaptation_retest(trials, "data/adaptation_retest.png")

    print("\nDone.")


if __name__ == "__main__":
    main()
