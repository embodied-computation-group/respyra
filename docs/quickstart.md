# Quick Start

## No-hardware demo

Test the PsychoPy display with a synthetic breathing signal (no belt needed):

```bash
python -m respyra.demos.demo_display
```

This opens a PsychoPy window showing a scrolling sinusoidal waveform. Press **SPACE** to place a marker, **ESCAPE** to quit.

## Belt connection test

With a Vernier Go Direct Respiration Belt powered on and nearby:

```bash
python -m respyra.demos.demo_belt_connection
```

This terminal-only script connects via BLE (with USB fallback), prints 100 force samples (~10 seconds), and disconnects.

## Threaded belt demo

Demonstrates the background thread + queue pattern used in the full experiment:

```bash
python -m respyra.demos.demo_threaded_belt
```

Runs for 10 seconds, draining queued samples and reporting the effective sample rate.

## Full experiment

Run the respiratory motor control tracking task:

```bash
respyra-task
# or equivalently:
python -m respyra.scripts.breath_tracking_task
```

This will:
1. Connect to the belt (BLE, USB fallback)
2. Open a participant info dialog
3. Run range calibration (15 s)
4. Run trials: baseline → countdown → tracking → feedback
5. Save data to `data/sub-{id}_ses-{session}_{timestamp}.csv`

Press **ESCAPE** at any time to end early (data up to that point is saved).

## Post-session visualization

After a session, generate a 6-panel summary figure:

```bash
respyra-plot data/sub-01_ses-001_2026-02-24.csv
# or equivalently:
python -m respyra.utils.vis.plot_session data/*.csv --no-show
```

The figure is saved as `{csv_stem}_summary.png` alongside the CSV.
