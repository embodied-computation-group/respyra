```{image} ../media/respyra_icon_transparent.png
:alt: respyra logo
:width: 200px
:align: center
```

# respyra

**Open-source toolbox for respiratory motor control tracking with visuomotor perturbation**

[![PyPI](https://img.shields.io/pypi/v/respyra?color=blue)](https://pypi.org/project/respyra/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](https://github.com/embodied-computation-group/respyra/blob/main/LICENSE)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue)](https://www.python.org/downloads/)

respyra is a Python toolbox that integrates a [Vernier Go Direct Respiration Belt](https://www.vernier.com/product/go-direct-respiration-belt/) with [PsychoPy](https://www.psychopy.org/) to enable real-time respiratory motor control tracking experiments. Participants follow a sinusoidal target with their breathing while receiving continuous visual biofeedback. The toolbox supports configurable experimental conditions including multi-frequency target waveforms and visuomotor perturbations (visual gain manipulation), in which the displayed breathing trace is amplified or attenuated relative to ground truth.

![Task schematic](../media/task_schematic_2.png)

## Key features

- **Real-time respiratory tracking** — live breathing waveform with sinusoidal target dot
- **Visuomotor perturbation** — configurable feedback gain to amplify or attenuate the visual trace
- **Composable conditions** — define multi-frequency, multi-segment waveforms from simple building blocks
- **Three feedback modes** — graded (continuous color), binary, or trinary error feedback
- **Automated calibration** — range calibration with percentile-based outlier rejection and saturation detection
- **Crash-resilient logging** — incremental CSV with per-row flush
- **Post-session visualization** — 6-panel summary figure for quick data quality checks
- **Non-blocking belt I/O** — background thread + queue architecture keeps PsychoPy's frame loop smooth

For the full scientific background and validation data, see the [accompanying paper](https://github.com/embodied-computation-group/respyra/tree/main/paper).

## Getting started

Install from PyPI:

```bash
pip install respyra
```

Then run a no-hardware demo:

```bash
python -m respyra.demos.demo_display
```

Or with a belt connected:

```bash
respyra-task
```

See {doc}`installation` and {doc}`quickstart` for full details.

```{toctree}
:maxdepth: 2
:hidden:

installation
quickstart
userguide
api/index
examples/index
troubleshooting
adapting_belt
```
