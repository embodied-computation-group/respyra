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
    "sphinx_design",
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
templates_path = ["_templates"]
html_title = f"respyra {release}"

# Project logo — displayed in the sidebar/header of the Sphinx site.
# Path is relative to the docs/ directory (where conf.py lives).
html_logo = "../media/respyra_icon.png"
html_favicon = "../media/respyra_icon.png"

# Theme options
html_theme_options = {
    "collapsiblesidebar": True,
}

# Context variables available in templates — used by the theme for
# "Edit on GitHub" and source links.
html_context = {
    "github_url": "https://github.com/embodied-computation-group/respyra",
    "github_version": "main",
    "doc_path": "docs/",
}
