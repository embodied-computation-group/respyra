# Roadmap

## Phase 1 — Condition Library

Expand the set of experimental conditions beyond the current slow-steady and perturbed-slow paradigms.

### New condition types

- **Box breathing** — square-wave target with configurable inhale/hold/exhale/hold durations (e.g., 4-4-4-4 s). Requires extending `TargetGenerator` beyond sinusoidal waveforms to support piecewise-linear or step-function segments.
- **Syncopated breathing** — asymmetric inhale/exhale ratios (e.g., 2 s inhale, 6 s exhale). Could be implemented as phase-shifted sinusoids or as custom waveform shapes.
- **Fast conditions** — higher-frequency sinusoidal targets (0.2–0.4 Hz) to probe tracking limits and establish difficulty scaling.
- **Oddball conditions** — baseline sinusoidal pattern with single-breath amplitude or frequency deviants inserted at unpredictable intervals. Requires a new segment type that injects transient perturbations into an otherwise regular waveform.
- **Ramp conditions** — frequency or amplitude that increases/decreases linearly across the tracking phase, for titrating individual tracking thresholds.

### Implementation

- Generalize `TargetGenerator` to accept arbitrary waveform functions (sine, square, sawtooth, piecewise) per segment.
- Add a `SegmentDef.waveform` parameter (default: `'sine'`).
- Create a condition library in `respyra/configs/` with pre-built condition sets that experimenters can import and combine.
- Add difficulty metadata to `ConditionDef` for adaptive trial ordering.

---

## Phase 2 — Expert Pilot Testing

Validate the task and toolbox with experienced respiratory researchers before naive participant testing.

### Goals

- Recruit 3–5 expert subjects (lab members, collaborators with respiratory psychophysiology experience).
- Run full sessions with the expanded condition set from Phase 1.
- Identify usability issues: instructions clarity, calibration robustness, visual feedback interpretability, session duration fatigue.
- Verify data quality: check for belt drift, signal saturation, dropped samples, timing precision.
- Test edge cases: participant with very shallow breathing, very deep breathing, irregular baseline.

### Deliverables

- Issue tracker populated with bugs and UX improvements found during piloting.
- Revised default parameters (calibration duration, tracking duration, feedback thresholds) based on pilot data.
- Standard operating procedure (SOP) document for research assistants.

---

## Phase 3 — Interoceptive Control Accuracy Study

First empirical study: characterize respiratory motor control accuracy in healthy naive participants using easy vs. hard trial contrasts.

### Design

- **N = 20–30** healthy naive participants.
- **Within-subjects** easy vs. hard manipulation:
  - Easy: slow sinusoidal (0.1 Hz), veridical feedback (gain = 1.0).
  - Hard: faster frequency (0.2–0.3 Hz), and/or perturbed feedback (gain > 1.0), and/or oddball deviants.
- **Outcome measures**: mean absolute error (MAE), RMSE, phase coherence between breathing signal and target, adaptation rate (error reduction over time within a trial).
- **Individual differences**: correlate tracking accuracy with self-report interoceptive measures (MAIA-2, body awareness questionnaires).

### Analysis plan

- Mixed-effects models: error ~ difficulty * trial + (1|participant).
- Test-retest reliability across sessions (subset of participants).
- Characterize learning effects within and across trials.

---

## Phase 4 — Analysis & Visualization Toolkit

Expand `respyra.utils` into a comprehensive analysis suite for respiratory tracking data.

### Planned features

- **Time-frequency analysis** — wavelet coherence between breathing signal and target waveform, instantaneous frequency estimation.
- **Phase analysis** — Hilbert transform to extract breathing phase, compute phase-locking value (PLV) to target.
- **Adaptive performance metrics** — sliding-window MAE, cumulative tracking score, learning curves.
- **Cross-session analysis** — merge multiple session CSVs, compute between-session reliability (ICC), plot longitudinal trajectories.
- **Group-level visualization** — spaghetti plots, group-mean error traces with confidence bands, condition-comparison forest plots.
- **Automated quality control** — flag sessions with excessive drift, signal dropout, or calibration anomalies.
- **Export utilities** — tidy dataframes ready for R/JASP/SPSS, BIDS-compatible output format.

---

## Phase 5 — Publication

Write and submit the toolbox paper and empirical study.

### Toolbox paper

- Target journal: JOSS (Journal of Open Source Software) or Behavior Research Methods.
- Content: toolbox architecture, validation data from Phases 2–3, usage tutorial, comparison to existing respiratory paradigms.
- Open science: all code on GitHub/PyPI, raw data on OSF, pre-registration of the empirical study.

### Empirical paper

- Target journal: Psychophysiology, Biological Psychology, or similar.
- Content: interoceptive control accuracy in healthy participants, easy vs. hard dissociation, individual differences, reliability.
- Pre-registration on OSF before data collection begins (Phase 3).

### LaTeX integration

- Paper drafts already live in `paper/` directory.
- Figures generated programmatically from `respyra.utils.vis` to ensure reproducibility.
