flask_app.py — web routes and analysis
==========================================

Database configuration and PostgreSQL URI generation are provided by
``module_6.src.db.config``. Configuration is resolved when needed; importing
the web module does not connect to PostgreSQL.

The factory ``module_6.src.web.app.flask_app.create_app`` accepts a configuration
mapping and optional scraper, cleaner, loader, and query functions. Run
``python -m module_6.src.web.run`` from the repository root.

.. list-table:: Route contract
   :header-rows: 1

   * - Method and path
     - Response
   * - GET ``/`` or ``/analysis``
     - Analysis HTML (200); database error HTML (500).
   * - POST ``/pull-data``
     - ``{"ok": true}`` after commit (200); ``{"busy": true}`` (409);
       ``{"ok": false, "error": "Data pull failed"}`` (500).
   * - GET ``/pull-status``
     - Status JSON (200): state, title, message, timestamps, and summary.
   * - POST ``/update-analysis``
     - Refreshed HTML (200); ``{"busy": true}`` (409); database error HTML (500).

The default pull uses the real Module-2 scraper/cleaner and Module-6 loader.
Tests replace dependencies through the factory. Work runs in the request
thread; status is shared by request threads in the same app process.

``/analysis`` and ``/update-analysis`` accept an optional integer ``limit``
query parameter. The default and maximum are 50; valid integers are clamped
to 1–50, and malformed values receive a generic HTTP 400 JSON error before
the analysis query runs. Limits bound returned rows, leaving aggregate
calculations over the complete matching dataset unchanged.

.. automodule:: module_6.src.web.app.flask_app
   :members: MAX_QUERY_LIMIT, clamp_query_limit, create_app, run_pull_pipeline, get_pull_status, update_pull_status, calculate_percentage, rounded_average, question_2, question_3, question_6, question_7, question_11, build_analysis_results, query_analysis, pull_data, pull_status_endpoint, index, update_analysis

The scaffold adds GET ``/health`` and POST ``/jobs``. Jobs support ``noop`` and
``scrape``; the latter uses the worker-side incremental scraper stand-in.
Database configuration is implemented independently in ``src/db/config.py``.
