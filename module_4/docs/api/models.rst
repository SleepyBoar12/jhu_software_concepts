models.py — database mapping
============================

Location: ``module_4/src/models.py``. ``Applicant`` maps the PostgreSQL
``applicants`` table. The module constructs ``database_url`` from the five
``PG*`` variables, creates an engine with connection health checks, and exposes
``SessionLocal`` as its reusable session factory. ``test_connection()`` is an
application diagnostic, rather than a pytest test; all test code remains in
``module_4/tests``.

.. autoclass:: module_4.src.models.Base

.. automodule:: module_4.src.models
   :members: Applicant, test_connection
