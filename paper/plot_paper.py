"""Generate final figures and tables for the respyra validation study paper.

Usage:
    py -3.10 paper/plot_paper.py data/sub-m_ses-*.csv

Generates (in paper/ directory):
    table1_session_stats.tex    — LaTeX table for main.tex
    table1_session_stats.txt    — console-readable version
    fig1_example_trials.png     — representative veridical + perturbed trial traces
    fig2_session_performance.png — session MAE, perturbation ratio, within-block adaptation
    fig3_reliability.png        — split-half reliability for visual MAE + perturbation ratio

Design rationale:
    - Veridical condition measures respiratory control ability
    - Perturbed condition measures sensorimotor flexibility (remapping under gain change)
    - Perturbation ratio (perturbed / veridical visual MAE) isolates remapping cost
    - "Visual error" = compensated_error (what the participant saw and tried to minimize)
    See paper/analysis_rationale.md for full conceptual framing.
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).parent))
from analysis import (  # noqa: E402
    compute_session_stats,
    compute_trial_stats,
    label_breath_phase,
    load_sessions,
)

OUT_DIR = Path(__file__).parent

# -- Theme (dark, matching plot_session.py) --------------------------------

BG_COLOR = "#0e0e1a"
PANEL_BG = "#1a1a2e"
TEXT_COLOR = "white"
TICK_COLOR = "#aaaaaa"
GRID_ALPHA = 0.15
SPINE_COLOR = "#333333"

COLOR_SLOW = "#5b9bd5"
COLOR_PERT = "#e05cda"
COLOR_FORCE = "#00e676"
COLOR_TARGET = "#ffa726"
COLOR_INSP = "#64b5f6"
COLOR_EXP = "#ef5350"
COLOR_RATIO = "#ffa726"

COND_COLORS = {"slow_steady": COLOR_SLOW, "perturbed_slow": COLOR_PERT}
COND_LABELS = {"slow_steady": "Veridical", "perturbed_slow": "Perturbed (2\u00d7)"}

SESSION_COLORS = ["#66bb6a", "#42a5f5", "#ffa726", "#ef5350"]  # S1-S4


def style_ax(ax, title="", xlabel="", ylabel=""):
    """Apply dark theme styling to an axes."""
    ax.set_facecolor(PANEL_BG)
    ax.set_title(title, color=TEXT_COLOR, fontsize=11, fontweight="bold", pad=8)
    ax.set_xlabel(xlabel, color=TEXT_COLOR, fontsize=10)
    ax.set_ylabel(ylabel, color=TEXT_COLOR, fontsize=10)
    ax.tick_params(colors=TICK_COLOR, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)
    ax.grid(True, alpha=GRID_ALPHA, color="white")


def save_fig(fig, name):
    path = OUT_DIR / name
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"  Saved: {path}")
    plt.close(fig)


# ======================================================================
# Table 1: Session Descriptive Statistics
# ======================================================================


def generate_table1(session_stats: pd.DataFrame) -> None:
    """Generate LaTeX and text table files."""

    # Text version
    lines = []
    header = (
        f"{'Ses':>3} {'N':>3} {'Dur':>6} {'BPM':>10} {'Depth(N)':>12} "
        f"{'Cyc':>4} {'CV':>5} {'Slow MAE':>12} {'Pert MAE':>12} "
        f"{'Slow Comp':>12} {'Pert Comp':>12}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    for _, r in session_stats.iterrows():
        lines.append(
            f"{int(r.session):3d} {int(r.n_trials):3d} {r.duration_min:6.1f} "
            f"{r.breathing_rate_bpm_mean:5.1f}\u00b1{r.breathing_rate_bpm_sd:4.2f} "
            f"{r.breathing_depth_n_mean:6.2f}\u00b1{r.breathing_depth_n_sd:5.2f} "
            f"{int(r.n_cycles):4d} {r.cycle_cv_mean:5.3f} "
            f"{r.slow_raw_mae:.3f}\u00b1{r.slow_raw_sd:.3f} "
            f"{r.pert_raw_mae:.3f}\u00b1{r.pert_raw_sd:.3f} "
            f"{r.slow_comp_mae:.3f}\u00b1{r.slow_comp_sd:.3f} "
            f"{r.pert_comp_mae:.3f}\u00b1{r.pert_comp_sd:.3f}"
        )

    txt = "\n".join(lines)
    txt_path = OUT_DIR / "table1_session_stats.txt"
    txt_path.write_text(txt, encoding="utf-8")
    print(f"  Saved: {txt_path}")
    print(txt)

    # LaTeX version
    tex_lines = [
        r"\begin{table}[ht]",
        r"\centering",
        r"\caption{Session-level descriptive statistics for the single-participant "
        r"validation study (4~sessions, 12~trials each). BPM = breaths per minute; "
        r"Depth = peak-to-trough breathing amplitude; MAE = mean absolute error; "
        r"Comp = compensated (gain-adjusted) error. Values are $M \pm SD$ across trials.}",
        r"\label{tab:session_stats}",
        r"\small",
        r"\begin{tabular}{c c r r@{\,}l r@{\,}l r r@{\,}l r@{\,}l}",
        r"\toprule",
        r"Session & $N$ & Dur. & \multicolumn{2}{c}{BPM} & "
        r"\multicolumn{2}{c}{Depth (N)} & Cycles & "
        r"\multicolumn{2}{c}{Verid.\ MAE (N)} & "
        r"\multicolumn{2}{c}{Pert.\ MAE (N)} \\",
        r"\midrule",
    ]

    for _, r in session_stats.iterrows():
        tex_lines.append(
            f"  {int(r.session)} & {int(r.n_trials)} & {r.duration_min:.1f} & "
            f"{r.breathing_rate_bpm_mean:.1f} & $\\pm$ {r.breathing_rate_bpm_sd:.2f} & "
            f"{r.breathing_depth_n_mean:.2f} & $\\pm$ {r.breathing_depth_n_sd:.2f} & "
            f"{int(r.n_cycles)} & "
            f"{r.slow_comp_mae:.3f} & $\\pm$ {r.slow_comp_sd:.3f} & "
            f"{r.pert_comp_mae:.3f} & $\\pm$ {r.pert_comp_sd:.3f} \\\\"
        )

    # Total row
    ss = session_stats
    tex_lines.append(r"\midrule")
    tex_lines.append(
        f"  Total & {int(ss.n_trials.sum())} & {ss.duration_min.sum():.1f} & "
        f"{ss.breathing_rate_bpm_mean.mean():.1f} & $\\pm$ "
        f"{ss.breathing_rate_bpm_mean.std():.2f} & "
        f"{ss.breathing_depth_n_mean.mean():.2f} & $\\pm$ "
        f"{ss.breathing_depth_n_mean.std():.2f} & "
        f"{int(ss.n_cycles.sum())} & "
        f"{ss.slow_comp_mae.mean():.3f} & $\\pm$ {ss.slow_comp_mae.std():.3f} & "
        f"{ss.pert_comp_mae.mean():.3f} & $\\pm$ {ss.pert_comp_mae.std():.3f} \\\\"
    )

    tex_lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]

    tex_path = OUT_DIR / "table1_session_stats.tex"
    tex_path.write_text("\n".join(tex_lines), encoding="utf-8")
    print(f"  Saved: {tex_path}")


# ======================================================================
# Figure 1: Example Trials (2 rows × 3 cols)
# ======================================================================


def _pick_representative_trial(trials, session, condition):
    """Pick the trial closest to the session-condition median visual MAE."""
    sub = trials[(trials["session"] == session) & (trials["condition"] == condition)]
    median_mae = sub["comp_mae"].median()
    idx = (sub["comp_mae"] - median_mae).abs().idxmin()
    return int(sub.loc[idx, "trial_num"])


def plot_example_trials(df: pd.DataFrame, trials: pd.DataFrame) -> None:
    """2×3: representative veridical (top) and perturbed (bottom) trial traces."""
    fig, axes = plt.subplots(2, 3, figsize=(16, 8))
    fig.patch.set_facecolor(BG_COLOR)

    rep_session = 2
    trial_configs = [
        ("slow_steady", "A  Veridical Trial", COLOR_SLOW),
        ("perturbed_slow", "B  Perturbed Trial (2\u00d7 gain)", COLOR_PERT),
    ]

    tracking = df[(df["phase"] == "tracking") & (df["session"] == rep_session)].copy()
    tracking["breath_phase"] = label_breath_phase(tracking["target_force"].values)

    for row, (cond, row_title, _cond_color) in enumerate(trial_configs):
        tnum = _pick_representative_trial(trials, rep_session, cond)
        grp = tracking[(tracking["trial_num"] == tnum) & (tracking["condition"] == cond)].copy()

        t_sec = grp["timestamp"].values
        force = grp["force_n"].values
        target = grp["target_force"].values
        comp_err = grp["compensated_error"].values
        phase = grp["breath_phase"].values

        ce = comp_err[~np.isnan(comp_err)]
        mae = np.mean(np.abs(ce))
        rmse = np.sqrt(np.mean(ce**2))
        ratio = rmse / mae if mae > 0 else 0

        # -- Col 1: Breathing trace --
        ax = axes[row, 0]
        style_ax(ax, row_title, xlabel="Time (s)", ylabel="Force (N)")

        # Breath phase shading
        for i in range(len(t_sec) - 1):
            color = COLOR_INSP if phase[i] == "inspiration" else COLOR_EXP
            ax.axvspan(t_sec[i], t_sec[i + 1], color=color, alpha=0.08)

        ax.plot(t_sec, target, color=COLOR_TARGET, linewidth=1.2, alpha=0.7, label="Target")
        ax.plot(t_sec, force, color=COLOR_FORCE, linewidth=0.8, alpha=0.9, label="Breathing")
        ax.legend(
            fontsize=8,
            facecolor=PANEL_BG,
            edgecolor=SPINE_COLOR,
            labelcolor=TEXT_COLOR,
            loc="upper right",
        )

        # -- Col 2: Visual error trace --
        ax = axes[row, 1]
        style_ax(
            ax,
            f"Visual Error   MAE = {mae:.3f} N   RMSE/MAE = {ratio:.2f}",
            xlabel="Time (s)",
            ylabel="Visual Error (N)",
        )

        for i in range(len(t_sec) - 1):
            color = COLOR_INSP if phase[i] == "inspiration" else COLOR_EXP
            ax.plot(t_sec[i : i + 2], comp_err[i : i + 2], color=color, linewidth=0.8, alpha=0.8)

        ax.axhline(0, color=TICK_COLOR, linewidth=0.5, alpha=0.5)
        ax.axhline(mae, color=TEXT_COLOR, linewidth=0.5, alpha=0.3, linestyle=":")
        ax.axhline(-mae, color=TEXT_COLOR, linewidth=0.5, alpha=0.3, linestyle=":")

        # -- Col 3: Error histogram --
        ax = axes[row, 2]
        style_ax(ax, "Error Distribution", xlabel="Visual Error (N)", ylabel="Density")

        insp_err = comp_err[phase == "inspiration"]
        exp_err = comp_err[phase == "expiration"]
        all_err = np.concatenate([insp_err[~np.isnan(insp_err)], exp_err[~np.isnan(exp_err)]])
        bins = np.linspace(all_err.min() * 1.1, all_err.max() * 1.1, 50)

        ax.hist(
            insp_err[~np.isnan(insp_err)],
            bins=bins,
            density=True,
            color=COLOR_INSP,
            alpha=0.6,
            label="Inspiration",
            edgecolor="none",
        )
        ax.hist(
            exp_err[~np.isnan(exp_err)],
            bins=bins,
            density=True,
            color=COLOR_EXP,
            alpha=0.6,
            label="Expiration",
            edgecolor="none",
        )
        ax.axvline(0, color=TICK_COLOR, linewidth=0.8, alpha=0.5)

        # Normal reference
        x_norm = np.linspace(bins[0], bins[-1], 200)
        sd = np.std(ce)
        ax.plot(
            x_norm,
            stats.norm.pdf(x_norm, 0, sd),
            color=TEXT_COLOR,
            linewidth=1,
            alpha=0.4,
            linestyle="--",
            label="Normal",
        )
        ax.legend(fontsize=8, facecolor=PANEL_BG, edgecolor=SPINE_COLOR, labelcolor=TEXT_COLOR)

    fig.suptitle(
        "Figure 1: Representative Trial Traces (Session 2)",
        color=TEXT_COLOR,
        fontsize=13,
        fontweight="bold",
        y=1.01,
    )
    fig.tight_layout()
    save_fig(fig, "fig1_example_trials.png")


# ======================================================================
# Figure 2: Session Performance (2×2)
# ======================================================================


def plot_session_performance(df: pd.DataFrame, trials: pd.DataFrame) -> None:
    """2×2: session MAE + perturbation ratio (top), within-block by condition (bottom)."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor(BG_COLOR)

    sessions = sorted(trials["session"].unique())

    # -- Top-left: Visual MAE by session --
    ax = axes[0, 0]
    style_ax(ax, "A  Visual MAE by Session", xlabel="Session", ylabel="Visual MAE (N)")

    for cond, color in COND_COLORS.items():
        means = []
        sems = []
        for s in sessions:
            vals = trials[(trials["session"] == s) & (trials["condition"] == cond)]["comp_mae"]
            means.append(vals.mean())
            sems.append(vals.sem())
        ax.errorbar(
            sessions,
            means,
            yerr=sems,
            fmt="o-",
            color=color,
            linewidth=2,
            markersize=7,
            capsize=4,
            label=COND_LABELS[cond],
        )
        # Individual trial dots
        for s in sessions:
            vals = trials[(trials["session"] == s) & (trials["condition"] == cond)]["comp_mae"]
            jitter = np.random.default_rng(42).uniform(-0.08, 0.08, len(vals))
            ax.scatter(
                [s] * len(vals) + jitter, vals, color=color, s=15, alpha=0.3, edgecolors="none"
            )

    ax.set_xticks(sessions)
    ax.legend(fontsize=9, facecolor=PANEL_BG, edgecolor=SPINE_COLOR, labelcolor=TEXT_COLOR)

    # -- Top-right: Perturbation ratio by session --
    ax = axes[0, 1]
    style_ax(
        ax,
        "B  Perturbation Ratio by Session",
        xlabel="Session",
        ylabel="Perturbed / Veridical MAE",
    )

    ratio_means = []
    all_trial_ratios = []
    for s in sessions:
        v_mean = trials[(trials["session"] == s) & (trials["condition"] == "slow_steady")][
            "comp_mae"
        ].mean()
        p_vals = trials[(trials["session"] == s) & (trials["condition"] == "perturbed_slow")][
            "comp_mae"
        ]
        session_ratio = p_vals.mean() / v_mean
        ratio_means.append(session_ratio)
        # Per-trial ratios
        for v in p_vals:
            all_trial_ratios.append({"session": s, "ratio": v / v_mean})

    tr = pd.DataFrame(all_trial_ratios)

    ax.plot(sessions, ratio_means, "o-", color=COLOR_RATIO, linewidth=2.5, markersize=9, zorder=4)

    for s in sessions:
        vals = tr[tr["session"] == s]["ratio"]
        jitter = np.random.default_rng(42).uniform(-0.1, 0.1, len(vals))
        ax.scatter(
            [s] * len(vals) + jitter,
            vals,
            color=COLOR_RATIO,
            s=25,
            alpha=0.4,
            edgecolors="none",
            zorder=3,
        )

    ax.axhline(1.0, color=TICK_COLOR, linewidth=1, alpha=0.5, linestyle=":")
    ax.text(sessions[0] - 0.1, 1.05, "no cost", color=TICK_COLOR, fontsize=8)
    ax.set_xticks(sessions)

    # Trend annotation
    rho, p_rho = stats.spearmanr(sessions, ratio_means)
    ax.text(
        0.05,
        0.95,
        f"rho={rho:+.3f}, p={p_rho:.3f}",
        transform=ax.transAxes,
        color=COLOR_RATIO,
        fontsize=9,
        va="top",
        fontfamily="monospace",
    )

    # -- Bottom-left: Veridical within-block --
    ax = axes[1, 0]
    style_ax(
        ax,
        "C  Veridical: Within-Block Tracking",
        xlabel="Trial within block",
        ylabel="Raw MAE (N)",
    )

    verid = trials[trials["condition"] == "slow_steady"]
    grand_means = verid.groupby("block_trial")["raw_mae"].mean()
    grand_sems = verid.groupby("block_trial")["raw_mae"].sem()

    for i, s in enumerate(sessions):
        ss = verid[verid["session"] == s]
        ax.plot(
            ss["block_trial"],
            ss["raw_mae"],
            "o-",
            color=SESSION_COLORS[i],
            linewidth=1,
            markersize=5,
            alpha=0.5,
            label=f"S{s}",
        )

    ax.fill_between(
        grand_means.index,
        grand_means - grand_sems,
        grand_means + grand_sems,
        color=COLOR_SLOW,
        alpha=0.2,
    )
    ax.plot(
        grand_means.index,
        grand_means,
        "o-",
        color=COLOR_SLOW,
        linewidth=2.5,
        markersize=7,
        label="Mean",
        zorder=5,
    )

    ax.set_xticks(range(1, 7))
    ax.legend(fontsize=8, facecolor=PANEL_BG, edgecolor=SPINE_COLOR, labelcolor=TEXT_COLOR, ncol=3)

    # -- Bottom-right: Perturbed within-block --
    ax = axes[1, 1]
    style_ax(
        ax,
        "D  Perturbed: Within-Block Adaptation",
        xlabel="Trial within block",
        ylabel="Visual MAE (N)",
    )

    pert = trials[trials["condition"] == "perturbed_slow"]
    grand_means = pert.groupby("block_trial")["comp_mae"].mean()
    grand_sems = pert.groupby("block_trial")["comp_mae"].sem()

    for i, s in enumerate(sessions):
        ss = pert[pert["session"] == s]
        ax.plot(
            ss["block_trial"],
            ss["comp_mae"],
            "o-",
            color=SESSION_COLORS[i],
            linewidth=1,
            markersize=5,
            alpha=0.5,
            label=f"S{s}",
        )

    ax.fill_between(
        grand_means.index,
        grand_means - grand_sems,
        grand_means + grand_sems,
        color=COLOR_PERT,
        alpha=0.2,
    )
    ax.plot(
        grand_means.index,
        grand_means,
        "o-",
        color=COLOR_PERT,
        linewidth=2.5,
        markersize=7,
        label="Mean",
        zorder=5,
    )

    ax.set_xticks(range(1, 7))
    ax.legend(fontsize=8, facecolor=PANEL_BG, edgecolor=SPINE_COLOR, labelcolor=TEXT_COLOR, ncol=3)

    fig.suptitle(
        "Figure 2: Session Performance and Within-Block Adaptation",
        color=TEXT_COLOR,
        fontsize=13,
        fontweight="bold",
        y=1.01,
    )
    fig.tight_layout()
    save_fig(fig, "fig2_session_performance.png")


# ======================================================================
# Figure 3: Reliability (1×2)
# ======================================================================


def _spearman_brown(r):
    return 2 * r / (1 + abs(r))


def plot_reliability(trials: pd.DataFrame) -> None:
    """Single split-half scatter for visual MAE across both conditions."""
    fig, ax = plt.subplots(1, 1, figsize=(6, 5.5))
    fig.patch.set_facecolor(BG_COLOR)

    sessions = sorted(trials["session"].unique())

    # Build split-half pairs
    pairs = []
    for (sess, cond), block in trials.groupby(["session", "condition"]):
        block = block.sort_values("block_trial")
        odd = block[block["block_trial"].isin([1, 3, 5])].reset_index(drop=True)
        even = block[block["block_trial"].isin([2, 4, 6])].reset_index(drop=True)
        for i in range(min(len(odd), len(even))):
            pairs.append(
                {
                    "session": sess,
                    "condition": cond,
                    "odd": odd.iloc[i]["comp_mae"],
                    "even": even.iloc[i]["comp_mae"],
                }
            )
    sh = pd.DataFrame(pairs)

    style_ax(
        ax,
        "Split-Half Reliability (Visual MAE)",
        xlabel="Odd-trial MAE (N)",
        ylabel="Even-trial MAE (N)",
    )

    cond_markers = {"slow_steady": "o", "perturbed_slow": "s"}

    # Plot: color = session, shape = condition, unfilled
    for cond in COND_COLORS:
        marker = cond_markers[cond]
        for s_idx, s in enumerate(sessions):
            sub = sh[(sh["condition"] == cond) & (sh["session"] == s)]
            ax.scatter(
                sub["odd"],
                sub["even"],
                facecolors="none",
                edgecolors=SESSION_COLORS[s_idx],
                s=60,
                linewidths=1.5,
                marker=marker,
                alpha=0.85,
                zorder=3,
            )

    # Legend
    legend_handles = []
    for cond, marker in cond_markers.items():
        legend_handles.append(
            ax.scatter(
                [],
                [],
                facecolors="none",
                edgecolors=TICK_COLOR,
                s=60,
                linewidths=1.5,
                marker=marker,
                label=COND_LABELS[cond],
            )
        )
    for s_idx, s in enumerate(sessions):
        legend_handles.append(
            ax.scatter(
                [],
                [],
                facecolors="none",
                edgecolors=SESSION_COLORS[s_idx],
                s=60,
                linewidths=1.5,
                marker="o",
                label=f"S{s}",
            )
        )

    all_vals = pd.concat([sh["odd"], sh["even"]])
    lim = (0, all_vals.max() * 1.15)
    ax.plot(lim, lim, color=TICK_COLOR, linewidth=0.8, alpha=0.4, linestyle="--")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_aspect("equal")

    r = sh["odd"].corr(sh["even"])
    sb = _spearman_brown(r)
    ax.text(
        0.05,
        0.95,
        f"r = {r:.3f}\nSB reliability = {sb:.3f}",
        transform=ax.transAxes,
        color=TEXT_COLOR,
        fontsize=9,
        verticalalignment="top",
        fontfamily="monospace",
    )
    ax.legend(
        handles=legend_handles,
        fontsize=8,
        facecolor=PANEL_BG,
        edgecolor=SPINE_COLOR,
        labelcolor=TEXT_COLOR,
        ncol=2,
    )

    fig.suptitle(
        "Figure 3: Split-Half Reliability",
        color=TEXT_COLOR,
        fontsize=13,
        fontweight="bold",
        y=1.02,
    )
    fig.tight_layout()
    save_fig(fig, "fig3_reliability.png")


# ======================================================================
# Figure 4: QC Session Summary (from respyra plot_session)
# ======================================================================


def plot_qc_session(csv_path: str) -> None:
    """Generate the 6-panel QC summary for a single session using respyra."""
    # Import the QC plotting module
    import importlib.util

    qc_module_path = Path(__file__).parent.parent / "respyra" / "utils" / "vis" / "plot_session.py"
    spec = importlib.util.spec_from_file_location("plot_session_qc", qc_module_path)
    qc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qc)

    session_df = qc.load_session(csv_path)
    fig = qc.plot_session(session_df, csv_path)
    fig.suptitle(
        "Figure 4: Example Session QC Summary (Session 1)",
        color=TEXT_COLOR,
        fontsize=13,
        fontweight="bold",
        y=1.0,
    )
    save_fig(fig, "fig4_qc_session.png")


# ======================================================================
# Main
# ======================================================================


def main():
    if len(sys.argv) < 2:
        print("Usage: py -3.10 paper/plot_paper.py data/sub-m_ses-*.csv")
        sys.exit(1)

    paths = []
    for arg in sys.argv[1:]:
        paths.extend(glob.glob(arg))
    if not paths:
        print("No CSV files found.")
        sys.exit(1)

    print(f"Loading {len(paths)} session file(s)...")
    df = load_sessions(paths)
    trials = compute_trial_stats(df)
    session_stats = compute_session_stats(df, trials)

    print(f"\nTotal: {len(trials)} trials across {trials['session'].nunique()} sessions\n")

    print("=== Table 1 ===")
    generate_table1(session_stats)

    print("\n=== Figures ===")
    plot_example_trials(df, trials)
    plot_session_performance(df, trials)
    plot_reliability(trials)

    # Figure 4: QC summary for session 1
    ses1_path = sorted(p for p in paths if "ses-001" in p)
    if ses1_path:
        plot_qc_session(ses1_path[0])
    else:
        print("  Warning: session 1 CSV not found, skipping fig4")

    print("\nDone. All outputs in paper/")


if __name__ == "__main__":
    main()
