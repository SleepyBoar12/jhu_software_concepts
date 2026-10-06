models.py — database mapping
================================

``Applicant`` preserves the Module-3 PostgreSQL table contract.
``create_session_factory`` resolves the configured PostgreSQL URL and creates
an engine without connecting at import time. ``SessionLocal`` opens a CLI
session and disposes its engine afterward.

.. automodule:: module_4.src.models
   :members: Applicant, create_session_factory, SessionLocal, test_connection

Database configuration
--------------------------

.. automodule:: module_4.src.database
   :members: get_database_url, connection_string
