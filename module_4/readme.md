Geunyong Son
Johns Hopkins University Fall 2026
------------------------------------------------
I install pytest and sphinx. Afterwards, I installed the packages
in src/requirements.txt for the codes to run.

Run commands from the repository root (`jhu_software_concepts`):

```bash
python -m pytest module_4/tests
python -m module_4.src.flask_app
python -m module_4.src.orm_queries
```

The tests import modules with `from module_4.src import flask_app` (and the
corresponding names for other modules). Imports between modules in `src` use
relative imports, such as `from .models import Applicant`. The `__init__.py`
files are empty, and pytest does not need a `pythonpath` setting.

Module 4 does not include live scraping or cleaning scripts. Tests use
`monkeypatch.setattr(flask_app, "run_pull_pipeline", fake_pull)` to supply
predictable pulls. Button tests return a fake summary; database and integration
tests pass test records through the real loader and use an isolated PostgreSQL
schema. Without the monkeypatch replacement, Pull Data reports that live data
collection is unavailable. Coverage measures `module_4.src`.

Tests mock database connections and server startup while exercising the real
validation, file reading, analysis, error handling, and command-line code.
Every test uses one of these five pytest markers:

| Test file | Marker | Coverage |
| --- | --- | --- |
| `tests/test_flask_page.py` | `web` | Flask pages, routes, errors, and server startup |
| `tests/test_buttons.py` | `buttons` | Pull Data and Update Analysis behavior |
| `tests/test_analysis.py` | `analysis` | SQL/ORM queries, analysis, and formatting |
| `tests/test_db_insert.py` | `db` | Loading, validation, configuration, and database inserts |
| `tests/test_integration_end_to_end.py` | `integration` | Pull, update, rendering, and repeated pulls |

Run a selected category, such as the analysis tests:

```bash
python -m pytest module_4/tests -m analysis --no-cov
```

Use `--no-cov` for a selected category because the 100% coverage requirement
applies to the full suite. Unknown markers are rejected with `--strict-markers`.

The full test suite also runs the database and integration tests against an
isolated PostgreSQL schema. The coverage requirement remains 100% for all
Python modules in `module_4.src`.

GitHub Actions runs this suite on pushes and pull requests using a PostgreSQL 16
service. The workflow supplies `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and
`PGPASSWORD` for the service's `test_db` database and creates an empty `src/.env`
to satisfy the application's environment-file requirement. No GitHub secrets
are needed for this temporary test database.

The workflow runs `python -m pytest tests -v --require-postgres` from `module_4`.
The `--require-postgres` option makes database connection or schema creation
failures fail the test run. Local runs without this option still skip database
tests when PostgreSQL is unavailable. To require PostgreSQL locally, run this
from the repository root with your database settings configured:

```bash
python -m pytest module_4/tests -v --require-postgres
```
