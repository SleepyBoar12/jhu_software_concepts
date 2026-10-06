"""Build API documentation without credentials, a database, or live ETL."""

import os
from pathlib import Path
import sys

repository_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(repository_root))

project = "GradCafe Application"
author = "Geunyong Son"
copyright = "2026, Geunyong Son"
release = "Module 4"
extensions = ["sphinx.ext.autodoc", "sphinx.ext.viewcode"]
root_doc = "index"
exclude_patterns = ["Thumbs.db", ".DS_Store"]
autodoc_member_order = "bysource"
autodoc_typehints = "none"
# Keep symbolic defaults instead of publishing build-machine filesystem paths.
autodoc_preserve_defaults = True
html_theme = "sphinx_rtd_theme"
html_title = "GradCafe application documentation"
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "/")
html_theme_options = {"navigation_depth": 3}
