# Analysis Rationale: Respiratory Tracking Error Metrics

## Task Design

The breath tracking task presents a visual target waveform (sinusoid) and real-time
feedback of the participant's breathing force. The participant tries to match their
breathing trace to the target. Two conditions:

- **Veridical**: feedback gain = 1.0. The screen shows actual breathing.
- **Perturbed (2×)**: feedback gain = 2.0. The screen amplifies breathing amplitude,
  forcing the participant to remap the visual-respiratory relationship.

This borrows from the visuomotor adaptation literature (prism adaptation, force field
perturbations, visuomotor rotations) and applies the same logic to respiratory control.

## What the Two Conditions Measure

- **Veridical** → **respiratory control ability**: can the participant learn the
  visual-respiratory mapping and track the target accurately?
- **Perturbed** → **sensorimotor flexibility**: when the mapping changes (gain
  shift), can the participant remap and adapt?

These are distinct constructs. The perturbation is not simply "harder tracking" — it
probes the capacity to remap sensorimotor relationships, which is a different process
from basic tracking.

## Error Definitions

- **Raw error** = `target_force − force_n`. The physical deviation of actual breathing
  from the target waveform. In veridical trials, this is the only error that matters.

- **Visual error** (called `compensated_error` in code) = `target_force − force_n × gain`.
  The deviation between the target and the displayed feedback. This is what the
  participant sees and tries to minimize. For veridical trials (gain=1), visual error
  = raw error. For perturbed trials (gain=2), they diverge.

- **MAE** = mean absolute error. Primary summary metric — average deviation in Newtons.

- **RMSE/MAE ratio** = error distribution shape. Theoretical value for normally
  distributed errors is ~1.253. Higher values indicate heavy-tailed errors
  (intermittent large deviations / attentional lapses). Lower values indicate
  uniform errors (consistent bias).

### Why "visual error" not "compensated error"

"Compensated" is opaque jargon. "Visual error" communicates what it is: the error in
the visual feedback, i.e., the discrepancy the participant actually experienced on
screen and was trying to minimize. Consider renaming `compensated_error` →
`visual_error` in future code and paper text.

## Recommended Metrics

### Primary: Visual MAE (compensated MAE)

- Directly interpretable (Newtons of deviation from target as displayed)
- Works across gain conditions
- Reflects what the participant was optimizing (the visuomotor loop)
- Standard in motor adaptation literature
- Normally distributed for veridical trials (Shapiro-Wilk p=.17)

### Secondary

| Metric | What it captures |
|---|---|
| Veridical MAE | Baseline respiratory tracking ability |
| Perturbed visual MAE | Adapted performance under the remapped gain |
| Within-block slope (T1→T6) | Adaptation rate — how quickly the participant remaps |
| Slope trend across sessions | Whether adaptation capacity degrades (fatigue) |
| RMSE/MAE ratio | Control consistency — steady errors vs. intermittent lapses |

### For Individual / Group Differences

For studies with multiple participants, two key metrics:

1. **Veridical MAE** — baseline respiratory control accuracy. Individual differences
   here reflect basic ability to learn and maintain a visual-respiratory mapping.

2. **Perturbation ratio** = perturbed visual MAE / veridical MAE. This normalizes
   out baseline ability and isolates the cost of sensorimotor remapping. A participant
   with low veridical MAE and low perturbation ratio has both good control AND good
   adaptability. A participant with low veridical MAE but high perturbation ratio can
   control their breathing but struggles when the mapping changes.

   This ratio is analogous to the "adaptation index" in visuomotor rotation studies:
   it captures the relative cost of perturbation, independent of baseline performance.

## Why Visual Error > 0 Under Perturbation

The participant does not "know" the physical target. They only see the visual target
and their (amplified) feedback trace. The reason visual error is not zero under
perturbation is **not** because interoception pulls them toward the "real" target —
they have no access to the real target.

It is because 2× gain makes the visuomotor control loop harder:
- Every small movement is amplified on screen
- Corrections overshoot — small adjustments produce large visual changes
- Motor noise is amplified in the visual domain
- The result is more oscillation and less precise convergence

This is a control-theoretic effect (high loop gain → reduced stability margin), not
a sensory weighting effect.

## Validation Study Findings (N=1, 48 trials)

- Veridical MAE: 0.243 ± 0.079 N (stable across sessions)
- Perturbed visual MAE: 0.538 ± 0.281 N (degrades in sessions 3–4)
- Perturbation ratio: ~2.2× (perturbed roughly twice as hard as veridical)
- RMSE/MAE ratio: veridical ~1.25 (normal), perturbed ~1.50 (heavy-tailed)
- Within-block adaptation slope: S1 = −0.094 (improving), S4 = +0.058 (degrading)
  - Trend of slopes: r = +0.957, p = .043 — significant linear degradation
- S4 perturbed trials show extreme kurtosis (mean 10.6) with max errors up to 10N
- Inspiration consistently harder than expiration (marginal for MAE, p = .002 for
  RMSE/MAE ratio under perturbation)
- Fatigue degrades remapping capacity specifically — veridical MAE remains stable
  while perturbed performance collapses
