flask_app.py — web routes and analysis
==========================================

This module also provides ``get_database_url`` and ``connection_string`` for
environment configuration and PostgreSQL URI generation. Configuration is
resolved when needed; importing the module does not connect to PostgreSQL.

The factory ``module_5.src.flask_app.create_app`` accepts a configuration
mapping and optional scraper, cleaner, loader, and query functions. Run
``python -m module_5.src.flask_app`` from the repository root.

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

The default pull uses the real Module-2 scraper/cleaner and Module-4 loader.
Tests replace dependencies through the factory. Work runs in the request
thread; status is shared by request threads in the same app process.

``/analysis`` and ``/update-analysis`` accept an optional integer ``limit``
query parameter. The default and maximum are 50; valid integers are clamped
to 1–50, and malformed values receive a generic HTTP 400 JSON error before
the analysis query runs. Limits bound returned rows, leaving aggregate
calculations over the complete matching dataset unchanged.

.. automodule:: module_5.src.flask_app
   :members: MAX_QUERY_LIMIT, clamp_query_limit, get_database_url, connection_string, create_app, run_pull_pipeline, get_pull_status, update_pull_status, calculate_percentage, rounded_average, question_2, question_3, question_6, question_7, question_11, build_analysis_results, query_analysis, pull_data, pull_status_endpoint, index, update_analysis
