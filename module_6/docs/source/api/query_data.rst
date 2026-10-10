query_data.py — SQL analysis
================================

Location: ``module_6/src/worker/etl/query_data.py``. The module defines SQL expressions
for the admissions questions and exposes helpers for printing answers and
selecting one applicant by URL. ``get_applicant_by_url()`` uses a bound
parameter and returns a dictionary or ``None``. Its statement uses
``sql.SQL`` with ``sql.Identifier`` for every selected column, table name,
and filter column. The URL and limit are passed separately to ``execute``.

All SELECT execution paths default to a maximum of 50 returned rows.
``run_query()`` wraps a trusted Psycopg SQL object in a SELECT with a bound
``LIMIT``. This limits output rows while preserving counts and averages over
all matching applicants. ORM queries use an equivalent bound SQLAlchemy limit.
CREATE TABLE and INSERT/UPSERT statements do not use a SELECT row limit.

Limits must be integers and are clamped to 1–50. Malformed values are rejected.
Each querying module defines its own maximum of 50. ``query_data.py``,
``orm_queries.py``, and ``flask_app.py`` each validate configurable limits
locally; the fixed count queries in ``load_data.py`` and ``models.py`` use
their local maximum directly.
The analysis and update-analysis endpoints accept ``?limit=25`` and return
HTTP 400 with a generic error for an invalid limit. They continue to return
aggregate reports and do not accept raw SQL or applicant-search filters.

Run ``python -m module_6.src.worker.etl.query_data`` from the repository root to print the
SQL results using the configured PostgreSQL database.

.. automodule:: module_6.src.worker.etl.query_data
   :members: MAX_QUERY_LIMIT, clamp_query_limit, format_value, get_applicant_by_url, run_query, main
