flask_app.py — web routes and analysis
======================================

Location: ``module_4/src/flask_app.py``. The module exposes ``app`` as its Flask
application. Run ``python -m module_4.src.flask_app`` from the repository root.

.. list-table:: Route contract
   :header-rows: 1
   :widths: 25 25 50

   * - Method and path
     - Function
     - Response and behavior
   * - GET ``/`` or ``/analysis``
     - ``index()``
     - Render fresh analysis with HTTP 200; return an error page with HTTP 500
       on a SQLAlchemy database error.
   * - POST ``/pull-data``
     - ``pull_data()``
     - Start the worker and render the page; reject a concurrent pull with
       HTTP 409. Rendering can return HTTP 500 if the database is unavailable.
   * - GET ``/pull-status``
     - ``pull_status_endpoint()``
     - Return status JSON with HTTP 200.
   * - POST ``/update-analysis``
     - ``update_analysis()``
     - Render refreshed results; return HTTP 409 while a pull is running or
       HTTP 500 if analysis fails.

Status JSON contains ``state``, ``title``, ``message``, ``started_at``,
``finished_at``, and ``summary``. States are ``idle``, ``running``, ``success``,
and ``error``. Completed-pull summaries contain loader row counts. The default
``run_pull_pipeline()`` raises ``NotImplementedError`` in Module 4; its worker
records the error in status. Tests replace that hook with deterministic data.

.. automodule:: module_4.src.flask_app
   :members: run_pull_pipeline, get_pull_status, update_pull_status, pull_data_worker, calculate_percentage, rounded_average, question_2, question_3, question_6, question_7, question_11, build_analysis_results, pull_data, pull_status_endpoint, index, update_analysis
