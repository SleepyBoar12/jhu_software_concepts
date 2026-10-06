Architecture
================

Layers and responsibilities
-------------------------------

.. list-table:: Application layers
   :header-rows: 1
   :widths: 18 35 47

   * - Layer
     - Modules
     - Responsibility
   * - Web
     - ``module_4.src.flask_app`` and ``src/templates/index.html``
     - Serve analysis pages, accept pull/update requests, expose pull status,
       and format query results for the template.
   * - Extract and transform
     - ``module_2.scrape`` and ``module_2.clean``
     - Check robots.txt, save survey HTML with Selenium, then group main,
       detail, and comment rows into applicant dictionaries.
   * - Load
     - ``module_4.src.load_data``
     - Validate required fields, dates, and scores; normalize optional values;
       batch records and upsert them in a transaction.
   * - Database and queries
     - PostgreSQL, ``module_4.src.models``, ``query_data``, and ``orm_queries``
     - Persist the applicants table, enforce unique URLs, manage sessions, and
       calculate SQL and ORM analyses.

Data flow
-------------

.. code-block:: text

   GradCafe survey pages
       │ module_2.scrape: saved HTML
       ▼
   module_2.clean: applicant dictionaries / JSON array
       │ optional upstream LLM enrichment
       ▼
   module_4.src.load_data: validation → batches → transactional upserts
       ▼
   PostgreSQL applicants table
       │ SQL queries / SQLAlchemy ORM
       ▼
   Flask analysis results → Jinja template → browser

The earlier ETL modules are reused in the default Flask pull pipeline and
documented in their existing locations. Tests inject scraper and cleaner
functions, then use the real loader for database and integration checks.

Database contract
---------------------

``applicants.p_id`` is an identity primary key. ``url`` is unique and is the
upsert key. ``program``, ``date_added``, ``url``, and ``status`` are required.
Other columns store comments, term, nationality classification, degree, scores,
and standardized program/university labels. Incoming
``applicant_status`` becomes ``status``, ``program_start`` becomes ``term``,
and hyphenated LLM keys become column names with underscores.

An identical URL and identical values produce no change. A changed record
updates its existing row. Missing incoming LLM labels preserve existing labels.
The loader reports ``processed_rows``, ``inserted_rows``, ``updated_rows``,
and ``total_rows``. Its connection commits on success and rolls back on error.
See :doc:`api/load_data` for the functions and :doc:`api/models` for the ORM.

Web requests and background work
------------------------------------

``create_app`` configures an independent application with injectable scraper,
cleaner, loader, and query functions. It accepts a ``DATABASE_URL`` override.
The default ``query_analysis`` returns the dictionary consumed by Jinja.
Database errors render an error page with HTTP 500. Counts use whole numbers;
score averages and percentages use two decimal places; unavailable values
use ``N/A``.

``pull_data`` claims the busy state under a lock, runs ETL in its request
thread, and returns JSON after commit. A second pull or an analysis update
while running receives HTTP 409 with ``{"busy": true}``. The page submits
with fetch and uses ``/pull-status`` to display progress. State belongs to
one Flask application process. See :doc:`operations` for deployment limits,
rollback behavior, and the uniqueness strategy.
