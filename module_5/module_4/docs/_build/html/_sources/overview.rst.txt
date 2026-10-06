Overview and setup
==================

Requirements and layout
-----------------------

Use Python 3.14 and a running PostgreSQL database. GitHub Actions tests against
PostgreSQL 16. Run the commands below from the repository root.

.. code-block:: text

   module_4/
   ├── src/              Flask, database loading, models, SQL and ORM queries
   ├── tests/            All Module 4 test code and fixtures
   ├── pytest.ini        Markers and the 100% coverage requirement
   ├── requirements.txt  Runtime, test, and Sphinx dependencies
   ├── README.md         Quick-start instructions
   └── docs/             Sphinx source, conf.py, and API reference

.. code-block:: bash

   git clone https://github.com/SleepyBoar12/jhu_software_concepts.git
   cd jhu_software_concepts
   python3.14 -m venv module_4/venv
   source module_4/venv/bin/activate
   python -m pip install -r module_4/requirements.txt

On Windows, activate the environment with
``module_4\venv\Scripts\Activate.ps1`` in PowerShell.

Database configuration
----------------------

Create a local database, for example ``createdb gradcafe`` using a PostgreSQL
role permitted to create databases. Create ``module_4/src/.env`` with settings
for that role:

.. code-block:: ini

   PGHOST=localhost
   PGPORT=5432
   PGDATABASE=gradcafe
   PGUSER=postgres
   PGPASSWORD=your-local-password

.. list-table:: Required environment variables
   :header-rows: 1
   :widths: 25 75

   * - Variable
     - Meaning
   * - ``PGHOST``
     - PostgreSQL hostname, such as ``localhost``.
   * - ``PGPORT``
     - PostgreSQL port, usually ``5432``; must be an integer.
   * - ``PGDATABASE``
     - Existing database containing the application table.
   * - ``PGUSER``
     - PostgreSQL login role. Database tests also require schema creation.
   * - ``PGPASSWORD``
     - Password for that role.

The current application reads these five variables; it does **not** read
``DATABASE_URL``. SQLAlchemy constructs its URL from them. Existing process
environment values take precedence over ``.env`` values. Even when the five
variables are exported, ``module_4/src/.env`` must exist: use
``touch module_4/src/.env`` when supplying settings from the environment.
The file is ignored by Git.

Create the applicants table
---------------------------

Initialize an empty table before opening the analysis page:

.. code-block:: bash

   python -c 'from module_4.src.load_data import load_cleaned_records; print(load_cleaned_records([]))'

This uses the loader's real table definition and commits the transaction.
To load records, call ``load_cleaned_records(records)`` with a list or iterable
of cleaned dictionaries. For example, the repository includes a JSON array
produced in Module 2:

.. code-block:: python

   import json
   from pathlib import Path
   from module_4.src.load_data import load_cleaned_records

   records = json.loads(
       Path("module_2/cleaned/applicant_data.json").read_text(encoding="utf-8")
   )
   print(load_cleaned_records(records))

Validation requires ``program``, ``date_added`` (for example ``Oct 03, 2026``),
``url``, and ``applicant_status``. Optional scores must be finite numbers.
The ``llm-generated-program`` and ``llm-generated-university`` fields can be
provided by an earlier enrichment step; analyses that use them depend on that
enrichment being available.

``python -m module_4.src.load_data`` instead reads **one JSON object per line**
from ``module_4/cleaned/llm_extended_applicant_data.json``. Supply that file
before using the command; its name ends in ``.json`` but its expected format
is JSON Lines. The Module 2 JSON array should be loaded with the Python example
above, rather than passed to this JSON Lines reader.

Run the app and queries
-----------------------

.. code-block:: bash

   python -m module_4.src.flask_app

Open ``http://127.0.0.1:5000/analysis``. Both ``/`` and ``/analysis`` display
the latest committed data. An empty table produces zero counts and ``N/A``
where an average or percentage cannot be calculated.

.. code-block:: bash

   python -m module_4.src.query_data
   python -m module_4.src.orm_queries

The first command prints SQL analysis results; the second prints its ORM
analysis subset. ``Update Analysis`` refreshes queries. In this Module 4
implementation, ``Pull Data`` reports that live collection is unavailable.
Its successful behavior is exercised with test doubles; see :doc:`testing`.

Run tests and build docs
-------------------------

.. code-block:: bash

   python -m pytest module_4/tests -v --require-postgres
   python -m sphinx -b html -W --keep-going module_4/docs module_4/docs/_build/html

Database tests use temporary schemas in the configured database. Use a test
database and a role allowed to create schemas. The documentation build needs
the installed Python dependencies, but no PostgreSQL server or credentials.
Open ``module_4/docs/_build/html/index.html`` after building.

Troubleshooting
---------------

* ``Environment file not found`` during app/test startup: create
  ``module_4/src/.env``. Check that all five ``PG*`` variables are supplied.
* An HTTP 500 analysis page: confirm that PostgreSQL is running, the configured
  database exists, and the applicants table has been initialized.
* Database tests skip locally: use ``--require-postgres`` to expose connection
  or schema-permission errors. Use a role allowed to create schemas.
* A partial test run fails coverage: use ``--no-cov`` with marker or node
  selection; retain the 100% check for full-suite runs.
* ``Line ... is not valid JSON`` from the command-line loader: it expects JSON
  Lines, rather than a JSON array. Use ``load_cleaned_records`` for an array.
* Package-relative import errors: run ``python -m module_4.src.flask_app``
  from the repository root rather than executing ``src/flask_app.py`` directly.
