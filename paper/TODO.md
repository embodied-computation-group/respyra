# Paper 2: Validation Study TODO

## Experiment Design

- [x] Create validation config: `respyra/configs/validation_study.py`
- [x] 12 trials per session (6 slow_steady, 6 perturbed_slow), blocked
- [x] 4 breath cycles per trial (0.1 Hz → 40 s tracking duration)
- [x] Gain factor: 2.0× for perturbed condition
- [x] 4 sessions, counterbalanced (ABAB/BABA starting condition)
- [x] All sessions same day
- [x] Added recalibration option (SPACE accept, R redo)
- [x] Added compensated_error column to data output
- [x] Dot color uses compensated error (not raw) during perturbed trials

## Data Collection

- [x] Run session 1 (starts slow_steady)
- [x] Run session 2 (starts perturbed)
- [x] Run session 3 (starts slow_steady)
- [x] Run session 4 (starts perturbed)
- [x] Spot-check data files after each session
- [ ] Commit final dataset to data/validation/ as example data

## Session Notes

- **Session 1**: Calibration too deep — target amplitude was uncomfortably
  large for the rest of the session, especially in perturbed trials.
  Strong within-block adaptation in perturbed condition (comp MAE 1.17→0.63).
- **Session 2**: Best overall performance (comp MAE: slow=0.15, pert=0.26).
  Massive cross-session savings from S1.
- **Session 3**: Belt felt too tight. Made gain trials extremely difficult.
  Noted sensation of dead air / air hunger — could not breathe out fully,
  bottom of breath clipped off display even though lungs were far from empty.
  Performance degraded, negative adaptation (getting worse within block).
- **Session 4**: Fatigue evident. Perturbed performance worst since S1
  (block mean 0.65). Negative adaptation within perturbed block.

## Calibration Issues (Future Work)

The current 80% of max range calibration may be suboptimal:
- Restricting to 80% of a deep-breath calibration creates a narrow
  operating range that can feel claustrophobic
- With the gain perturbation (2×), the effective required breathing
  amplitude is halved, which can push participants into uncomfortably
  shallow breathing where they can't fully exhale
- The display clips at the calibrated range boundaries, so participants
  lose visual feedback at the extremes — exactly when they need it most
- Belt tightness interacts with calibration: a tight belt shifts the
  force baseline up and compresses the usable range further

Potential improvements to explore:
- [ ] Calibrate from normal breathing (not deep breaths) — capture
  comfortable range rather than maximum range
- [ ] Use a larger fraction of range (90%?) or adaptive padding
- [ ] Asymmetric calibration (more room below center for exhalation)
- [ ] Dynamic y-range that extends if the signal goes out of bounds
- [ ] Per-trial recalibration option (not just at session start)
- [ ] Account for gain factor in calibration (widen range for perturbed trials)

## Analysis

- [x] Per-trial MAE (raw and compensated)
- [x] Within-session adaptation curves
- [x] Cross-session savings (first perturbed trial across sessions)
- [x] Split-half reliability (odd vs even trials)
- [x] Asymptotic split-half (trials 3-6 only)
- [x] Test-retest of adaptation effect across sessions
- [ ] Formal stats for paper (if needed beyond descriptive for N=1)
- [ ] Address fatigue confound in interpretation

## Analysis Scripts

- `paper/plot_validation.py` — generates all validation figures
- `respyra/utils/vis/plot_session.py` — per-session 6-panel summary

## References

- [ ] Review and update reference list
- [ ] Add citations for adaptation/learning framing
- [ ] Check for recent respiratory interoception papers
- [ ] Cite visuomotor gain perturbation literature

## Paper Revision

- [ ] Update Method: blocked design, 4 cycles, 4 sessions, 2.0× gain,
  compensated error metric, counterbalancing scheme
- [ ] Update Results with validation data (48 trials)
- [ ] Update Discussion: adaptation, savings, fatigue, calibration limitations
- [ ] Update abstract with new results
- [ ] Update proof-of-concept framing → validation study framing
- [ ] Regenerate figures with new data
- [ ] Add calibration limitations paragraph to Discussion
