# Module 5: GradCafe application

Geunyong Son - Johns Hopkins University, Fall 2026.

The Flask application collects recent GradCafe admissions pages, cleans the
applicant records, saves them in PostgreSQL, and displays counts, percentages,
and averages. **Pull Data** collects and commits records. **Update Analysis**
reads the committed database records and refreshes the analysis page.

## Project layout

The application files live directly under `module_5/`:

```text
module_5/
├── src/                   # App, database queries, templates, and CSS
├── tests/                 # Unit and PostgreSQL integration tests
├── docs/                  # Sphinx documentation
├── dependency.svg
├── setup.py
├── pyproject.toml
├── requirements.txt
├── README.md
├── .env.example
├── pytest.ini
├── module_5_report.pdf
└── coverage_summary.txt
```

Python modules use the package name `module_5.src`, for example
`module_5.src.flask_app`. If you installed the project before this folder
reorganization, reinstall it with `python -m pip install --no-deps -e .` from
`module_5/` to refresh the package mappings.

## Prerequisites

- Python 3.14, matching the environment used for this project.
- A complete checkout of `jhu_software_concepts`, including both `module_2/` and
  `module_5/`. The installer uses the shared Module 2 scraper and cleaner.
- PostgreSQL running locally or through a database provider.
- Chrome for live scraping. Tests replace the scraper and do not launch Chrome.
- Graphviz, with its `dot` command on your PATH, for dependency graphs.
- The `uv` command if you choose the uv installation method.

On macOS, Graphviz and uv can be installed with Homebrew:

```bash
brew install graphviz uv
dot -V
uv --version
```

PostgreSQL, Chrome, and Graphviz's `dot` executable are system applications;
installing Python dependencies does not install them.

## Fresh Install

Choose **one** of the following methods. Run it from `module_5/` in the complete
repository checkout. Each example creates a new `.venv`; use an unused
environment directory when repeating a fresh installation.

### pip

```bash
cd /path/to/jhu_software_concepts/module_5
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
python -m pip check
```

### uv

```bash
cd /path/to/jhu_software_concepts/module_5
uv venv --python 3.14 .venv
source .venv/bin/activate
uv pip sync requirements.txt
uv pip install --no-deps -e .
uv pip check
```

`uv pip sync` makes the third-party packages match the pinned requirements
exactly. The following editable install adds this project without changing
those dependency versions. Repeat both commands when syncing again, because
the requirements file does not list the local project itself.

Both methods install the runtime dependencies and development tools, including
Flask, SQLAlchemy, psycopg, BeautifulSoup, Selenium, python-dotenv, pytest,
Pylint, pydeps, and Sphinx. Use `deactivate` to leave the virtual environment.

## Database configuration

Python installation and database provisioning are separate steps. Create a
PostgreSQL database and configure an account with the permissions needed for
your chosen operation. Analysis reads rows; Pull Data inserts and updates rows.
Table initialization requires an account permitted to create the table.

For a local PostgreSQL installation that allows your operating-system account
to connect, create the database once and configure its URL:

```bash
createdb applicants
export DATABASE_URL='postgresql:///applicants'
```

Skip `createdb` if the database already exists. For a hosted database or
password authentication, use your provider's PostgreSQL connection URI in
`DATABASE_URL` instead. Keep real credentials out of source control.

Initialize an empty applicants table once, using a database owner or setup
account:

```bash
python -c 'from module_5.src.load_data import load_cleaned_records; print(load_cleaned_records([]))'
```

The app accepts `DATABASE_URL`, or alternatively `DB_HOST`/`PGHOST`,
`PGDATABASE`, `PGUSER`, and optional `PGPORT` and `PGPASSWORD` environment
variables. An optional `src/.env` file is read from the source checkout
when using an editable install. Local `.env` files are excluded from the
installed distribution; configure environment variables for a regular install.

The existing loader executes `CREATE TABLE IF NOT EXISTS` during a pull. A
restricted application account must be compatible with that statement; table
creation is a separate setup responsibility. See the
[operations documentation](docs/source/operations.rst) for transaction
and busy-state behavior.

## Run the application

With the virtual environment active and PostgreSQL configured:

```bash
python -m flask --app module_5.src.flask_app:create_app run
```

Open <http://127.0.0.1:5000/analysis>. The analysis initially uses any records
already in PostgreSQL. Click **Pull Data** to collect recent records, then
**Update Analysis** to show the newly committed data. An empty initialized
database displays zero counts and `N/A` for unavailable averages.

Live scraping checks GradCafe's `robots.txt` and stops if access is disallowed.
Existing applicant URLs are updated when their data changes, rather than
creating duplicate rows.

The separate command-line SQL report is available with:

```bash
python -m module_5.src.query_data
```

## Tests and code quality

From `module_5/`, run:

```bash
python -m pytest tests --require-postgres
python -m pylint src
```

Database tests create and remove isolated schemas. Configure a dedicated test
database/account with permission to create and drop those schemas. The
`--require-postgres` option makes unavailable PostgreSQL an error rather than
silently skipping database tests. The test suite requires 100% statement
coverage and prevents live HTTP requests and browser startup.

## Dependency graph

Generate the required SVG in `module_5/`:

```bash
pydeps src --noshow -T svg -o dependency.svg \
  --reverse --max-bacon 0 --log ERROR \
  --only module_5.src module_2 \
  --rmprefix module_5.src.
```

With `--reverse`, an arrow from A to B means A imports B. This graph focuses on
the application modules and their shared Module 2 dependencies.

## Packaging and reproducibility

`setup.py` installs the `module_5` application, the shared `module_2` scraper
and cleaner, and the HTML/CSS assets. Explicit package mappings preserve the
existing imports while excluding virtual environments, tests, and local
credentials. `pyproject.toml` declares the setuptools build backend, and
`requirements.txt` pins the Python dependencies and tools.

Packaging makes imports consistent across local runs, tests, and CI. An
editable installation with `pip install -e .` or `uv pip install -e .` uses the
source files directly, so Python edits take effect without reinstalling the
application. uv can also read the setup metadata when resolving requirements.
Together, packaging, pinned dependencies, and fresh-install instructions make
the environment reproducible for another developer.

Use `python -m pip install .` or `uv pip install .` for a regular installation
from the same complete repository checkout. Installation is performed through
pip or uv, rather than by running `python setup.py install`.

## Documentation

From `module_5/`, build the existing Sphinx documentation:

```bash
python -m sphinx -b html -W --keep-going docs/source docs/build/html
```

The rendered documentation is written to `docs/build/html/index.html`.
The assignment report is [module_5_report.pdf](module_5_report.pdf).
