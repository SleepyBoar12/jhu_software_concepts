query_data.py — SQL analysis
================================

Location: ``module_4/src/query_data.py``. The module defines SQL expressions
for the admissions questions and exposes helpers for printing answers and
selecting one applicant by URL. ``get_applicant_by_url()`` uses a bound
parameter and returns a dictionary or ``None``.

Run ``python -m module_4.src.query_data`` from the repository root to print the
SQL results using the configured PostgreSQL database.

.. automodule:: module_4.src.query_data
   :members: format_value, get_applicant_by_url, run_query, main
