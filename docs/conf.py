"""Sphinx configuration for SimpleBook docs."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

project = "SimpleBook"
author = "Bradley Fallon"
current_year = datetime.now().year
copyright = f"{current_year}, {author}"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

master_doc = "index"
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

html_theme = "alabaster"
html_static_path = []

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "tasklist",
]

napoleon_google_docstring = True
napoleon_numpy_docstring = False

autodoc_typehints = "description"
autosummary_generate = True
