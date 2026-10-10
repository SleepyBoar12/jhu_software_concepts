models.py — database mapping
================================

``Applicant`` preserves the Module-3 PostgreSQL table contract.
``create_session_factory`` resolves the configured PostgreSQL URL and creates
an engine without connecting at import time. ``session_local`` opens a CLI
session and disposes its engine afterward.

.. automodule:: module_6.src.db.models
   :members: Applicant, create_session_factory, session_local, test_connection

Database configuration is provided by ``module_6.src.db.config`` and resolved
when a session factory is created. Models do not import Flask or ORM query helpers.
