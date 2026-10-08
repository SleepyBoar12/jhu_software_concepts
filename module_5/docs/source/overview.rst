Overview and setup
======================

Requirements
----------------

Use Python 3.14 and PostgreSQL. CI uses PostgreSQL 16. The live scraper also
requires Chrome; tests and documentation builds do not execute the scraper.
Run these commands from the repository root:

.. code-block:: bash

   python3.14 -m venv module_5/venv
   source module_5/venv/bin/activate
   python -m pip install -r module_5/requirements.txt
   python -m pip install --no-deps -e module_5

On Windows, activate ``module_5\venv\Scripts\Activate.ps1`` instead.

Database configuration
--------------------------

Set ``DATABASE_URL`` to the PostgreSQL URI supplied by your database provider.
For a local database using the current operating-system role:

.. code-block:: bash

   createdb gradcafe
   export DATABASE_URL=postgresql:///gradcafe

An optional ``module_5/src/.env`` can contain the variable instead. It is
ignored by Git. A configuration passed to ``create_app`` overrides the
process environment; process variables override the optional dotenv file.
Never commit connection credentials.

``postgresql://``, ``postgres://``, and ``postgresql+psycopg://`` URLs are
accepted. Query options such as ``sslmode`` and ``options`` are preserved.
Existing Module-3 installations may continue using ``PGHOST``, ``PGDATABASE``,
``PGUSER``, optional ``PGPORT`` (default 5432), and ``PGPASSWORD`` when no URL
is provided. Database configuration is resolved when needed, so importing
modules and building documentation require neither configuration nor a server.

Initialize and load the table
---------------------------------

.. code-block:: bash

   python -c 'from module_5.src.load_data import load_cleaned_records; print(load_cleaned_records([]))'

Load a Module-2 JSON array with the public loader:

.. code-block:: python

   import json
   from pathlib import Path
   from module_5.src.load_data import load_cleaned_records

   records = json.loads(
       Path("module_2/cleaned/applicant_data.json").read_text(encoding="utf-8")
   )
   print(load_cleaned_records(records))

The input requires ``program``, ``date_added`` (for example ``Oct 03, 2026``),
``url``, and ``applicant_status``. Optional scores must be finite numbers.
LLM program/university fields remain optional, as in Module 3. Queries that
use these labels depend on upstream enrichment.

``python -m module_5.src.load_data`` reads one JSON object per line from
``module_5/cleaned/llm_extended_applicant_data.json``. Supply that file first;
use the example above for a JSON array instead of JSON Lines.

Run the app
---------------

.. code-block:: bash

   python -m module_5.src.flask_app

Open ``http://127.0.0.1:5000/analysis``. Both ``/`` and ``/analysis`` query
committed data. An empty table produces zero counts and ``N/A`` where a
percentage or average has no denominator. ``Pull Data`` collects recent
GradCafe pages and commits the cleaned records. ``Update Analysis`` refreshes
the results. See :doc:`operations` for concurrency and transaction policies.

The Flask factory is ``module_5.src.flask_app.create_app``. It accepts a
configuration dictionary and keyword-only ``scraper``, ``cleaner``, ``loader``,
and ``query`` functions. See :doc:`testing` for an offline example.

Run tests and documentation
-------------------------------

Use a test database whose role can create schemas:

.. code-block:: bash

   python -m pytest module_5/tests -m "web or buttons or analysis or db or integration" --require-postgres
   python -m sphinx -b html -W --keep-going module_5/docs/source module_5/docs/build/html

Open ``module_5/docs/build/html/index.html``. ``make -C module_5/docs html``
uses the same warnings-as-errors policy. On Windows use ``docs\make.bat html``
from ``module_5``.

Troubleshooting
-------------------

* ``Set DATABASE_URL``: provide a PostgreSQL URI in the environment or optional
  dotenv file. A configuration dictionary can override it for tests.
* Connection/authentication errors: verify the server, database, role, password,
  URI encoding, and provider SSL settings. Do not paste credentials into logs.
* HTTP 500 analysis: initialize the applicants table and check database access.
* HTTP 500 pull: inspect the server log; check Chrome availability, robots.txt
  permission, and input validity. Loader failures roll back the whole pull.
* Database tests skip: rerun with ``--require-postgres``. A test role must be
  allowed to create and drop temporary schemas.
* A selected subset fails coverage: add ``--no-cov`` for that partial run.
* CI cannot connect: check the Postgres service health check and ``DATABASE_URL``.
* JSON parsing fails: the CLI reader expects JSON Lines, not a JSON array.
* Relative imports fail: run modules with ``python -m`` from the repository root.
* Read the Docs fails: check :doc:`publishing`, the selected commit, dependency
  installation, and Sphinx warnings; no database settings should be necessary.
