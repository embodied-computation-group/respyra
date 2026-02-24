# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

**respyra** is a Python project for building psychophysical experiments that integrate the Vernier Go Direct Respiration Belt (GDX-RB) with PsychoPy. Experiments are written in pure Python (no PsychoPy Builder/GUI).

## Architecture

```
src/core/       → Reusable modules (breath belt I/O, display utils, data logging, etc.)
src/configs/    → Experiment parameter files (timing, conditions, display settings)
src/scripts/    → Runnable experiment sessions (import from core/ and configs/)
src/demos/      → Standalone single-feature test scripts
media/          → Stimulus assets (images, sounds, text files)
docs/context/   → Reference docs for agents and developers
```

**Code flow:** A script in `src/scripts/` imports modules from `src/core/` and parameters from `src/configs/`, loads stimuli from `media/`, runs the experiment, and saves data.

**Import convention:**
```python
from src.core import breath_belt
from src.core import display_utils
```

`src/` and `src/core/` are Python packages (`__init__.py` present).

## Key Dependencies

- **PsychoPy** (`pip install psychopy`) — experiment framework, visual stimuli, timing, data handling
- **godirect** (`pip3 install godirect`) — Vernier sensor USB/BLE driver
- **gdx wrapper** (not on PyPI) — must be copied from [VernierST/godirect-examples](https://github.com/VernierST/godirect-examples) `python/gdx/` into the project

## Context Documents

Read these before working on experiment code:

- **`docs/context/psychopy/psychopy_startup.md`** — PsychoPy Python API reference: Window setup, stimuli, timing (frame-based), input handling, trial/data management, monitor calibration, and coding rules
- **`docs/context/vernier/vernier.md`** — Vernier breath belt interface: channel mapping (Ch1=Force, Ch2=Resp Rate), gdx API lifecycle, connection patterns, gotchas

## Coding Conventions

- **PsychoPy code-only** — no Builder, no GUI workflow. Pure Python scripting.
- **Frame-based timing** for stimulus duration (`win.flip()` loop), never `core.wait()`.
- **Pre-create all stimuli** before trial loops. Never instantiate stimuli inside a loop.
- **`try/finally`** wrapping all experiments — `win.close()` and `core.quit()` in finally for PsychoPy; `stop()` then `close()` for Vernier belt.
- **Use PsychoPy's data module** (`ExperimentHandler`, `TrialHandler`, `StairHandler`) — do not write custom CSV logging.
- **Vernier belt:** always pass explicit args to `select_sensors()` and `start()` to prevent interactive prompts. Minimum sampling period 10 ms.
- **Monitor calibration** required for `'deg'`/`'cm'` units — use `monitors.Monitor` with physical screen dimensions and viewing distance.
- Experiment parameters belong in `src/configs/`, not hardcoded in scripts.

## Agents

The **experiment-builder** agent (`.claude/agents/experiment-builder.md`) handles experiment design, implementation, debugging, and optimization. It reads the context documents above and follows the project conventions. Use it for any PsychoPy or Vernier belt task.
