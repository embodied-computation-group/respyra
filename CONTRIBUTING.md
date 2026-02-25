# Contributing to respyra

Thanks for your interest in contributing to respyra! This guide covers everything
you need to get started.

## Development setup

respyra requires **Python 3.10** (PsychoPy does not yet support 3.11+).

```bash
git clone https://github.com/embodied-computation-group/respyra.git
cd respyra

# Create a Python 3.10 virtual environment
# Windows (Python Launcher)
py -3.10 -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3.10 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev and vis extras
pip install -e ".[dev,vis]"
```

This installs the runtime dependencies plus **ruff** (linter/formatter),
**pytest** and **pytest-cov** (testing), **pandas** and **matplotlib** (visualization).

## Running tests

The test suite lives in `tests/` and covers every module in `respyra/core/`.

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=respyra --cov-report=term-missing
```

### Mock strategy

PsychoPy and godirect cannot be installed in most CI environments, so
`tests/conftest.py` patches them out at the `sys.modules` level before any
test module imports `respyra.core.*`. The mock list includes:

- `psychopy` and its subpackages (`psychopy.visual`, `psychopy.core`, etc.)
- `godirect`

This happens at **module level** in `conftest.py` (not inside fixtures) because
Python caches imports — by the time a fixture runs, the import has already
happened. Tests then create focused mocks for the specific objects they need.

## Linting and formatting

respyra uses [ruff](https://docs.astral.sh/ruff/) for both linting and formatting.
Configuration lives in `pyproject.toml` under `[tool.ruff]`.

```bash
# Check for lint errors
ruff check .

# Auto-fix what can be fixed
ruff check . --fix

# Check formatting
ruff format --check .

# Apply formatting
ruff format .
```

**Enabled rule sets:** `E` `F` `W` (pyflakes/pycodestyle), `I` (isort import
ordering), `UP` (pyupgrade), `B` (flake8-bugbear), `SIM` (flake8-simplify).

CI runs `ruff check` and `ruff format --check` on every push and pull request —
both must pass.

## Code style

- **Line length:** 99 characters
- **Quote style:** ruff default (double quotes)
- **Import ordering:** handled by `ruff check` with the `I` (isort) rule
- **Target version:** Python 3.10

## Adding tests

Test files go in `tests/` and follow the naming convention `test_<module>.py`.
Each file tests the corresponding module in `respyra/core/`.

| Test file | Module under test |
|---|---|
| `test_breath_belt.py` | `respyra.core.breath_belt` |
| `test_data_logger.py` | `respyra.core.data_logger` |
| `test_display.py` | `respyra.core.display` |
| `test_events.py` | `respyra.core.events` |
| `test_target_generator.py` | `respyra.core.target_generator` |

### How conftest mocking works

The `conftest.py` at the root of `tests/` inserts `MagicMock` objects into
`sys.modules` for PsychoPy and godirect. This means:

- You can `from respyra.core import <module>` freely in tests — the imports
  won't fail even without PsychoPy installed.
- PsychoPy objects (e.g., `visual.Window`, `visual.TextStim`) are `MagicMock`
  instances. If your test needs specific return values, mock them explicitly
  in the test function.
- Shared fixtures like `simple_segment` and `simple_condition` are defined in
  `conftest.py` and available to all test files.

### What to mock

- **PsychoPy objects** — already handled by conftest; add focused patches if
  you need specific behavior (e.g., `window.size` returning `(1920, 1080)`).
- **File I/O** — use `tmp_path` (pytest built-in) for tests that write files.
- **gdx / breath belt** — mock the `GdxDevice` or belt reader; never connect
  to real hardware in tests.

## Project structure

See the [README](https://github.com/embodied-computation-group/respyra#project-structure) for a full directory tree and the
[documentation](https://embodied-computation-group.github.io/respyra/) for
detailed API reference and user guides.

## Submitting changes

1. **Fork** the repository and create a feature branch from `main`.
2. Make your changes, adding tests for new functionality.
3. Ensure **lint** and **tests** pass locally:
   ```bash
   ruff check .
   ruff format --check .
   pytest tests/ -v
   ```
4. Commit with a clear, descriptive message.
5. Open a **pull request** against `main`. CI will run lint and test checks
   automatically — both must pass before merging.

## The `gdx/` directory

The `respyra/core/gdx/` directory contains third-party code from
[VernierST/godirect-examples](https://github.com/VernierST/godirect-examples),
licensed under the **BSD 3-Clause License** (see `respyra/core/gdx/LICENSE`).

This directory is:
- **Excluded from ruff linting** (configured in `pyproject.toml`)
- **Not covered by the test suite**

Please do not modify files in `gdx/` unless there is a specific upstream
compatibility issue that requires a patch.
