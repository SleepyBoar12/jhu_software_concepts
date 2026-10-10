"""Package the Module-6 services, shared scraper, and runtime dependencies."""

from pathlib import Path
from setuptools import setup

project_directory = Path(__file__).resolve().parent
requirements = [
    line.strip()
    for line in (project_directory / "src" / "web" / "requirements.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    if line.strip() and not line.strip().startswith("#")
]

setup(
    name="jhu-gradcafe-module6",
    version="0.0.1",
    description="GradCafe data collection and Flask analysis application",
    python_requires=">=3.14",
    # List only application packages so virtual environments and tests are excluded.
    packages=[
        "module_6",
        "module_6.src",
        "module_6.src.db",
        "module_6.src.web",
        "module_6.src.web.app",
        "module_6.src.worker",
        "module_6.src.worker.etl",
        "module_2",
    ],
    # Preserve existing imports while using the shared scraper and cleaner source.
    package_dir={"module_6": ".", "module_2": "../module_2"},
    package_data={
        "module_6.src.db": ["init.sql"],
        "module_6.src.web": ["requirements.txt", "Dockerfile"],
        "module_6.src.web.app": ["templates/*.html", "static/*.css"],
        "module_6.src.worker": ["requirements.txt", "Dockerfile"],
    },
    # Include only the assets above, rather than local .env files or collected data.
    include_package_data=False,
    install_requires=requirements,
)
