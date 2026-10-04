Architecture
============

Layers and responsibilities
---------------------------

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
---------

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

The two earlier ETL modules are documented in their existing locations;
Module 4 does not currently wire them into a live Flask pull. Tests connect
the Flask hook to the real loader using fixed input records.

Database contract
-----------------

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
--------------------------------

``index()`` opens a SQLAlchemy session, computes eleven analyses, and renders
the page. Database errors render an error page with HTTP 500.
Counts use whole numbers; score averages and percentages use two decimal
places; unavailable values display ``N/A``.

``pull_data()`` sets shared status to ``running`` while holding a lock, starts
a daemon thread, and renders the page. The worker records ``success`` or
``error``. A second pull or an analysis update while running receives HTTP 409.
The browser polls ``/pull-status`` while a pull is running. Status is in memory
and belongs to the Flask process; it is not a persistent cross-process queue.
