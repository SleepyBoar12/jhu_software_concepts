Testing guide
=============

Run the suite
-------------

All Module 4 test code lives in ``module_4/tests``. Configure PostgreSQL and
``module_4/src/.env`` as described in :doc:`overview`. Run from the repository
root after activating the virtual environment:

.. code-block:: bash

   python -m pytest module_4/tests -v --require-postgres

``pytest.ini`` enables strict markers, measures ``module_4.src``, reports
missing lines, and requires **100% statement coverage** for the full suite.
The current suite contains 65 test cases, including parametrized cases.
Coverage alone does not prove that a real database test executed:
``--require-postgres`` fails setup when a connection or schema creation fails.
Without this option, unavailable database tests are skipped for local runs.

Markers and selection
---------------------

.. list-table:: Registered markers
   :header-rows: 1
   :widths: 15 35 50

   * - Marker
     - Test file
     - Scope
   * - ``web``
     - ``test_flask_page.py``
     - App configuration, routes, rendering, errors, and server startup.
   * - ``buttons``
     - ``test_buttons.py``
     - Pull/update behavior, progress, and busy-state HTTP 409 responses.
   * - ``analysis``
     - ``test_analysis.py``
     - SQL/ORM query behavior, empty results, and answer formatting.
   * - ``db``
     - ``test_db_insert.py``
     - Validation, loading, startup settings, real inserts, and idempotence.
   * - ``integration``
     - ``test_integration_end_to_end.py``
     - Real database flows through pull, update, rendering, and repeated pulls.

Use ``--no-cov`` when selecting part of the suite: the 100% requirement applies
to all application modules, so a partial run cannot satisfy it.

.. code-block:: bash

   python -m pytest module_4/tests -m web --no-cov
   python -m pytest module_4/tests -m buttons --no-cov
   python -m pytest module_4/tests -m analysis --no-cov
   python -m pytest module_4/tests -m db --no-cov --require-postgres
   python -m pytest module_4/tests -m integration --no-cov --require-postgres
   python -m pytest module_4/tests -m "web or buttons" --no-cov
   python -m pytest module_4/tests/test_buttons.py::test_pull_data_when_busy --no-cov

Expected routes and page selectors
----------------------------------

The Flask client calls routes directly and checks response status and rendered
text. Existing page tests look for ``Pull Data``, ``Update Analysis``,
``Analysis``, and ``Answer:``. Percentage tests expect strings such as
``12.30%``. These are Flask response tests; they do not execute browser
JavaScript or use Selenium.

The template also provides these stable selectors for manual or future browser
checks:

.. list-table:: UI contract
   :header-rows: 1
   :widths: 40 60

   * - Selector
     - Expected behavior
   * - ``#pull-data-form`` / ``#pull-data-button``
     - Submit POST ``/pull-data``; the button is disabled while running.
   * - ``#update-analysis-form`` / ``#update-analysis-button``
     - Submit POST ``/update-analysis``; the button is disabled while running.
   * - ``#pull-status-panel``
     - Hidden in the idle state; announces progress with ``role="status"``.
   * - ``#pull-status-title`` / ``#pull-status-message``
     - Display the worker's current title and message.
   * - ``#analysis-status-panel``
     - Announces that an analysis update is running.
   * - ``.analysis-card`` / ``.answer-label`` / ``.answer-grid``
     - Display each analysis question, ``Answer:``, and its result values.
   * - ``.error-panel[role="alert"]``
     - Display an analysis database error with HTTP 500.

Both GET ``/`` and GET ``/analysis`` render analysis. GET ``/pull-status``
returns status JSON. Busy POST requests return HTTP 409 and must not start a
second worker or run a new analysis.

Fixtures and doubles
--------------------

Shared fixtures are in ``tests/conftest.py``:

* ``valid_applicant`` supplies a complete, deterministic input record.
* ``fake_pg_environment`` sets predictable ``PG*`` values for mocked tests.
* ``mock_database`` replaces ``psycopg.connect`` with connection/cursor mocks,
  including their context managers; it does not open PostgreSQL.
* ``run_module`` exercises real command-line startup through ``runpy`` and
  restores the imported module afterwards.
* ``app`` replaces the session boundary and analysis builder, enables Flask
  testing, and supplies fixed answers; ``client`` returns its test client.
* ``set_pull_state`` isolates the shared status dictionary for each test.
* ``isolated_database`` creates a uniquely named PostgreSQL schema, redirects
  loader connections through its search path, creates the real applicants
  table, and drops that schema during teardown.

Button and database tests replace ``Thread`` with ``ImmediateThread``, which
runs the worker synchronously. They monkeypatch ``run_pull_pipeline`` with
either a fixed summary or a call to the real loader using fixed records.
No test needs access to GradCafe or an LLM service.

The ``integration_client`` fixture in ``test_integration_end_to_end.py`` binds
real SQLAlchemy sessions to the isolated schema and leaves the analysis code
active. It verifies inserted data, formatted answers, and overlapping pulls
without duplicate URLs. The database role must be able to create and drop
schemas in the test database.

GitHub Actions
--------------

``.github/workflows/tests.yml`` creates a PostgreSQL 16 service with a health
check, maps port 5432, supplies matching ``PG*`` settings, creates an empty
``src/.env``, and runs ``python -m pytest tests -v --require-postgres`` from
``module_4``. The service uses a temporary ``test_db`` database. The full run
must include database and integration tests and meet the coverage threshold.
