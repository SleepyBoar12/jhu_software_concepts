"""Package the GradCafe app, its Module-2 helpers, and pinned dependencies."""

from pathlib import Path
from setuptools import setup

project_directory = Path(__file__).resolve().parent
requirements = [
    line.strip()
    for line in (project_directory / "requirements.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    if line.strip() and not line.strip().startswith("#")
]

setup(
    name="jhu-gradcafe-module5",
    version="0.0.1",
    description="GradCafe data collection and Flask analysis application",
    python_requires=">=3.14",
    # List only application packages so virtual environments and tests are excluded.
    packages=[
        "module_5",
        "module_5.src",
        "module_2",
    ],
    # Preserve existing imports while using the shared scraper and cleaner source.
    package_dir={"module_5": ".", "module_2": "../module_2"},
    package_data={
        "module_5.src": ["templates/*.html", "static/*.css"],
    },
    # Include only the assets above, rather than local .env files or collected data.
    include_package_data=False,
    install_requires=requirements,
)
