# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path

# Add project root to sys.path so autodoc can import respyra even when the
# package is not pip-installed (e.g., CI doc builds on Python 3.12).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import respyra  # noqa: E402

# -- Project information -----------------------------------------------------

project = "respyra"
author = "Micah Allen"
copyright = "2026, Micah Allen"
release = respyra.__version__

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
]

# MyST (Markdown) settings
myst_enable_extensions = [
    "colon_fence",
    "fieldlist",
]

# Napoleon (NumPy-style docstrings)
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_param = True
napoleon_use_rtype = True

# Autodoc
autodoc_member_order = "bysource"
autodoc_mock_imports = [
    "psychopy",
    "godirect",
    "respyra.core.gdx",
]

# Intersphinx
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
}

# File suffixes
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# Exclude patterns
exclude_patterns = ["_build", "context"]

# -- HTML output -------------------------------------------------------------

html_theme = "python_docs_theme"
html_static_path = ["_static"]
html_title = f"respyra {release}"
