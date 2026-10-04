"""Build API documentation without reading credentials or connecting to a DB."""

import importlib
import os
from pathlib import Path
import sys
from unittest.mock import patch


repository_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repository_root))

project = "GradCafe Application"
author = "Geunyong Son"
copyright = "2026, Geunyong Son"
release = "Module 4"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
]
root_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
autodoc_member_order = "bysource"
autodoc_typehints = "none"
# Selenium and BeautifulSoup are only needed to execute the Module 2 ETL.
autodoc_mock_imports = ["selenium", "bs4"]

html_theme = "alabaster"
html_title = "GradCafe application documentation"
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "/")
html_theme_options = {
    "github_user": "SleepyBoar12",
    "github_repo": "jhu_software_concepts",
    "github_button": False,
}

# The application checks for src/.env at import time. Give its real modules
# harmless documentation-only settings inside this process, without creating
# a file, loading a user's .env, changing application code, or opening a DB.
environment_file = repository_root / "module_4" / "src" / ".env"
original_is_file = Path.is_file


def documentation_is_file(path):
    return path == environment_file or original_is_file(path)


with (
    patch.dict(os.environ, {
        "PGHOST": "localhost",
        "PGPORT": "5432",
        "PGDATABASE": "documentation_only",
        "PGUSER": "documentation_only",
        "PGPASSWORD": "documentation_only",
    }),
    patch("dotenv.load_dotenv", return_value=False),
    patch.object(Path, "is_file", documentation_is_file),
):
    for module_name in ("models", "load_data", "query_data", "orm_queries", "flask_app"):
        importlib.import_module(f"module_4.src.{module_name}")
