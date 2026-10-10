orm_queries.py — ORM analysis
=================================

Location: ``module_6/src/worker/etl/orm_queries.py``. These SQLAlchemy query functions are
shared by the web analysis builder. They cover counts, GPA averages, acceptance
percentages, and raw-text versus LLM-label matching. ``format_decimal()``
returns two decimal places or ``N/A``.

.. automodule:: module_6.src.worker.etl.orm_queries
   :members: MAX_QUERY_LIMIT, clamp_query_limit, question_1, question_4, question_5, question_8, question_9, question_10, format_decimal, collect_orm_results, main
