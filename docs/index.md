```{image} ../media/respyra_icon.png
:alt: respyra logo
:width: 200px
:align: center
```

# respyra

**A general-purpose respiratory motor control tracking toolbox for interoception research**

[![PyPI](https://img.shields.io/pypi/v/respyra?color=blue)](https://pypi.org/project/respyra/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](https://github.com/embodied-computation-group/respyra/blob/main/LICENSE)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue)](https://www.python.org/downloads/)
[![GitHub](https://img.shields.io/badge/GitHub-source-black?logo=github)](https://github.com/embodied-computation-group/respyra)

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

## Documentation

::::{grid} 2 2 3 3
:gutter: 3

:::{grid-item-card} Installation
:link: installation
:link-type: doc

Python 3.10 setup, PyPI install, platform notes
:::

:::{grid-item-card} Quick Start
:link: quickstart
:link-type: doc

Run demos and your first experiment in minutes
:::

:::{grid-item-card} User Guide
:link: userguide
:link-type: doc

Session flow, configuration, conditions, data output
:::

:::{grid-item-card} API Reference
:link: api/index
:link-type: doc

Auto-generated docs from source code docstrings
:::

:::{grid-item-card} Examples
:link: examples/index
:link-type: doc

Annotated walkthroughs of demos and experiment scripts
:::

:::{grid-item-card} Troubleshooting
:link: troubleshooting
:link-type: doc

BLE issues, sensor saturation, frame drops, and more
:::

:::{grid-item-card} Adapting the Belt
:link: adapting_belt
:link-type: doc

Swap in a different respiratory sensor
:::

::::

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
