Testing guide
=================

Run the complete suite
--------------------------

Activate the virtual environment and configure a test ``DATABASE_URL``.
From the repository root:

.. code-block:: bash

   python -m pytest module_5/module_4/tests -m "web or buttons or analysis or db or integration" --require-postgres

Or from ``module_4``:

.. code-block:: bash

   pytest -m "web or buttons or analysis or db or integration" --require-postgres

The suite requires 100% statement coverage of ``module_5.module_4.src``. The
``--require-postgres`` option fails if a database is unavailable, so CI cannot
silently skip the real database tests. Local runs without it can skip them.
Use ``--no-cov`` only when intentionally running a subset.

Markers
-----------

Every test must carry at least one of these markers. A collection hook checks
all collected tests before marker deselection and rejects unmarked tests.
``--strict-markers`` also rejects unregistered marks.

.. list-table:: Categories
   :header-rows: 1

   * - Marker
     - Coverage
   * - ``web``
     - Factory isolation, routes, HTML components, selectors, and errors.
   * - ``buttons``
     - JSON contracts, injected ETL calls, busy gating, and error responses.
   * - ``analysis``
     - Query/template dictionary keys, all percentages, rounding, and labels.
   * - ``db``
     - Module-3 schema, required fields, inserts, uniqueness, rollback, configuration.
   * - ``integration``
     - Real PostgreSQL pull → update → render and overlapping pulls.

.. code-block:: bash

   python -m pytest module_5/module_4/tests -m analysis --no-cov

Selectors and formatting
----------------------------

Tests use the Flask test client and BeautifulSoup, without manual clicking,
Selenium, or browser JavaScript execution. Stable button selectors are
``[data-testid="pull-data-btn"]`` and ``[data-testid="update-analysis-btn"]``.
The existing ``#pull-data-button`` and ``#update-analysis-button`` IDs remain.
Each question is an ``.analysis-card`` with an ``.answer-label`` containing
``Answer:``. Values appear in ``.answer-grid dd``.

Tests inspect every percentage token in the rendered page and require a full
regex match of ``\d+\.\d{2}%``. They also cover zero, 100%, rounding, and trailing
zeroes. Every real analysis card must contain an Answer label. The real
``query_analysis`` result must contain ``analysis_results`` with the complete
question/answer dictionary keys expected by the template. Separate database
tests verify an explicit set of all fifteen Module-3 applicant field names.

Fixtures and injection
--------------------------

``create_app`` accepts replaceable functions:

.. code-block:: python

   from module_5.module_4.src.flask_app import create_app

   record = {
       "program": "Computer Science, Example University",
       "date_added": "Oct 03, 2026",
       "url": "https://example.com/result/1",
       "applicant_status": "Accepted",
   }
   app = create_app(
       {"TESTING": True},
       scraper=lambda directory: [],
       cleaner=lambda directory: [record],
       loader=lambda records: {
           "processed_rows": 1, "inserted_rows": 1, "updated_rows": 0,
       },
       query=lambda: {"analysis_results": []},
   )
   assert app.test_client().post("/pull-data").json == {"ok": True}

``scraper`` receives a temporary output directory; ``cleaner`` reads it;
``loader`` receives cleaned dictionaries; ``query`` takes no arguments and
returns the template context. Each factory call owns its status and lock.

Shared fixtures in ``tests/conftest.py`` provide:

* ``valid_applicant``: complete, deterministic input.
* ``app`` and ``client``: a fresh app with injected functions and its test client.
* ``set_pull_state``: observable, isolated busy state without delays.
* ``no_live_scraping``: fail immediately on live HTTP access or Chrome startup.
* ``mock_database``: connection/cursor mocks for validation and CLI tests.
* ``run_module``: execute CLI entry points with external effects mocked.
* ``isolated_database``: unique schema and a URL whose search path targets it;
  teardown drops only that schema.

A concurrency test uses threading events to hold a fake scraper while another
client verifies both busy responses and no update/loader calls. It releases the
scraper in ``finally``. Event timeouts bound failures; no arbitrary sleeps are
used. The end-to-end test checks empty results, a real committed pull, updated
analysis, all percentage tokens, and Answer labels.

Rollback tests set the batch size to one, write a valid first batch, then fail
on invalid input or a PostgreSQL constraint in the second batch. They require
HTTP 500, released busy state, and zero persisted rows.

CI
--

``.github/workflows/tests.yml`` starts PostgreSQL 16, waits for its health
check, supplies ``DATABASE_URL``, and runs the entire marker-selected suite
with ``--require-postgres``. The database and its run-specific credentials are
disposable. ``documentation.yml`` separately builds Sphinx with warnings as
errors. Test execution takes seconds; live scraping is never part of CI.
