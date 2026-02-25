# Sci-Docs-Reviewer Agent Memory

## Project Structure (verified 2026-02-25)

- Package root: `respyra/` (NOT `src/` -- CLAUDE.md still references `src/` but the code lives under `respyra/`)
- `respyra/__init__.py`: version 0.1.0
- `respyra/core/`: breath_belt.py, display.py, events.py, data_logger.py, target_generator.py, gdx/ (vendor)
- `respyra/configs/`: breath_tracking.py (main), test_experiment.py
- `respyra/scripts/`: breath_tracking_task.py, test_belt_display.py, generate_screenshots.py
- `respyra/demos/`: demo_belt_connection.py, demo_display.py, demo_threaded_belt.py
- `respyra/utils/vis/`: plot_session.py
- `docs/context/`: psychopy/, vernier/, intero/ (literature reviews)
- `paper/main.tex`: APA7 toolbox paper (single-author, Micah Allen, Aarhus University)
- Build: hatchling, pyproject.toml, entry points: respyra-task, respyra-plot, respyra-screenshots

## Documentation Status (audited 2026-02-25)

### Docstring Quality
- `breath_belt.py`: EXCELLENT. Full NumPy-style docstrings on all public methods. Module-level docstring with usage examples.
- `display.py`: GOOD. NumPy-style docstrings present. Module-level docstring is minimal.
- `events.py`: GOOD. NumPy-style docstrings on all 3 public functions. Clean.
- `data_logger.py`: GOOD. NumPy-style docstrings, module-level usage example.
- `target_generator.py`: EXCELLENT. Full NumPy-style docstrings, module-level usage example.
- `gdx/gdx.py`: POOR. Third-party vendor code. Google-style docstrings (not NumPy). Class-level state, no type hints. Not our code to modify.

### Key Drift Issues
- CLAUDE.md references `src/core/`, `src/configs/`, `src/scripts/`, `src/demos/` -- all should be `respyra/`
- CLAUDE.md import convention shows `from src.core import breath_belt` -- should be `from respyra.core import breath_belt`
- The experiment-builder agent file likely has same stale references

### Terminology
- "respiration force" or "force" (in Newtons) for Ch1 data -- consistent across codebase
- "feedback gain" or "gain" for the visuomotor perturbation multiplier
- "tracking error" = target_force - actual_force (signed), "absolute tracking error" = |error|
- Units: N (Newtons), Hz, ms, seconds
- Colors: "graded" / "binary" / "trinary" feedback modes

### Sphinx Documentation (updated 2026-02-25)
- Full Sphinx site at https://embodied-computation-group.github.io/respyra/
- Built via GitHub Actions (`.github/workflows/docs.yml`) on push to main
- `docs/conf.py`: python_docs_theme, myst_parser, napoleon, autodoc with mock imports for psychopy/godirect/gdx
- `docs/index.md`: landing page with icon, badges, feature list, toctree
- Pages: installation.md, quickstart.md, userguide.md, troubleshooting.md, adapting_belt.md, api/index, examples/index
- `html_logo` and `html_favicon` set to `../media/respyra_icon_transparent.png`
- docs/context/ files are agent/developer reference only (excluded from Sphinx via exclude_patterns)

### README.md (updated 2026-02-25)
- Centered icon (respyra_icon_transparent.png), badges (PyPI, docs, license, Python 3.10)
- PyPI install is primary method; dev install is secondary
- Links to full docs site, PyPI, and paper
- Dedicated Documentation section with links to all doc pages
- License section at bottom

### Icon Assets (media/)
- `respyra_icon.png`: white background version
- `respyra_icon_transparent.png`: transparent background (used in README, docs, Sphinx logo)
