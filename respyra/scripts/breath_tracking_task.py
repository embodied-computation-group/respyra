#!/usr/bin/env python3
"""Respiratory tracking task — CLI entry point.

Runs the breath tracking experiment using the configuration specified
via ``--config``.  See :mod:`respyra.core.runner` for the experiment
logic and composable phase functions.

Examples::

    # Default config
    respyra-task

    # Built-in config by short name
    respyra-task --config demo

    # Custom config file
    respyra-task --config experiments/my_study.py
"""

import argparse

from respyra.configs.experiment_config import load_config
from respyra.core.runner import run_experiment


def main(config_source=None):
    """Entry point for ``respyra-task`` CLI and direct invocation."""
    parser = argparse.ArgumentParser(
        description="Run a respyra breath tracking experiment.",
    )
    parser.add_argument(
        "--config",
        "-c",
        default=config_source,
        help=(
            "Config source: short name (e.g. 'demo'), "
            "dotted module path (e.g. 'respyra.configs.demo'), "
            "or path to a .py file (e.g. 'experiments/my_study.py'). "
            "Defaults to the base ExperimentConfig."
        ),
    )
    args = parser.parse_args()
    cfg = load_config(args.config)
    run_experiment(cfg)


if __name__ == "__main__":
    main()
