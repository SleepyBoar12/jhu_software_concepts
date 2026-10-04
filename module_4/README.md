# Module 4: GradCafe tests and documentation

[Published Sphinx documentation on Read the Docs](https://jhu-software-concepts-sleepyboar12.readthedocs.io/en/latest/)

Geunyong Son — Johns Hopkins University, Fall 2026.

Use Python 3.14 and PostgreSQL. From the repository root:

```bash
python3.14 -m venv module_4/venv
source module_4/venv/bin/activate
python -m pip install -r module_4/requirements.txt
```

Set `DATABASE_URL` to your PostgreSQL connection URI, either in your shell or
in the optional, gitignored `module_4/src/.env` file. For a local PostgreSQL
installation using your current operating-system role:

```bash
createdb gradcafe
export DATABASE_URL=postgresql:///gradcafe
python -c 'from module_4.src.load_data import load_cleaned_records; print(load_cleaned_records([]))'
python -m module_4.src.flask_app
```

Use your database provider's connection URI when authentication is required;
keep credentials out of source control. A `DATABASE_URL` passed to
`create_app({"DATABASE_URL": ...})` overrides environment settings. Earlier
Module-3 `PGHOST`, `PGDATABASE`, `PGUSER`, optional `PGPORT` and `PGPASSWORD`
settings remain supported when no URL is supplied. No `.env` file is required.

Open http://127.0.0.1:5000/analysis. Pull Data uses the Module-2 scraper and
cleaner and the real PostgreSQL loader. Live scraping requires Chrome and
permission from the source site's robots.txt. Tests use injected functions
and never start a browser, make live HTTP requests, or scrape the internet.

`POST /pull-data` returns `200 {"ok": true}` after commit and
`500 {"ok": false, "error": "Data pull failed"}` on failure. While a pull is
running, both POST routes return `409 {"busy": true}` without doing work.
`POST /update-analysis` otherwise returns refreshed HTML. The page uses fetch
for its buttons and exposes `data-testid="pull-data-btn"` and
`data-testid="update-analysis-btn"`.

Run the complete suite against a test database:

```bash
python -m pytest module_4/tests -m "web or buttons or analysis or db or integration" --require-postgres
```

From `module_4`, the exact selection command is:

```bash
pytest -m "web or buttons or analysis or db or integration" --require-postgres
```

Every collected test must carry `web`, `buttons`, `analysis`, `db`, or
`integration`; collection fails for unmarked tests, even when marker selection
would otherwise hide them. The suite requires 100% statement coverage.
Use `--no-cov` for an intentionally partial run. Without `--require-postgres`,
local database tests may skip if PostgreSQL is unavailable; CI requires them.

Tests cover JSON contracts, observable busy state, every rendered percentage,
all Answer labels, template dictionary keys, schema compatibility, inserts,
duplicate pulls, rollback after an earlier batch was written, and an end-to-end
pull → update → render flow. BeautifulSoup checks HTML and regex checks two
decimal places. Each database test creates and drops its own schema.

GitHub Actions starts PostgreSQL 16, supplies `DATABASE_URL`, and runs the full
marker-selected suite. Service credentials are disposable values derived from
the CI run. The application schema and URL uniqueness policy match Module 3.

Build Sphinx HTML with warnings treated as errors:

```bash
python -m sphinx -b html -W --keep-going module_4/docs/source module_4/docs/build/html
```

Open `module_4/docs/build/html/index.html`. Documentation includes setup,
architecture, autodoc for the scraper, cleaner, loader, queries, and Flask
routes, testing, operational notes, and troubleshooting. Builds require no
database, credentials, Chrome, or network calls from application code.

Read the Docs uses the repository-root `.readthedocs.yaml`. See the
[publishing guide](docs/source/publishing.rst) for project setup and rebuilds,
and [operational notes](docs/source/operations.rst) for busy-state and
transaction policies.
