load_data.py — validation and loading
=========================================

Location: ``module_4/src/load_data.py``. Use ``load_cleaned_records(records)``
for cleaned dictionaries. The optional ``database_url`` argument overrides
``DATABASE_URL``. ``read_records(path)`` instead reads JSON Lines
and yields already prepared records for ``load_records()``.

.. code-block:: python

   from module_4.src.load_data import load_cleaned_records

   summary = load_cleaned_records([{
       "program": "Computer Science, Test University",
       "date_added": "Oct 03, 2026",
       "url": "https://www.thegradcafe.com/result/example-1",
       "applicant_status": "Accepted",
       "program_start": "Fall 2026",
       "gpa": "3.90",
   }])

Rows are batched in groups of 1,000. Table creation and upserts happen in the
same transaction. Invalid required fields, dates, and non-finite scores raise
``ValueError``. Missing files raise ``FileNotFoundError``. A repeated URL uses
the existing row; see :doc:`../architecture` for the upsert contract.

.. automodule:: module_4.src.load_data
   :members: required_text, optional_text, optional_decimal, prepare_record, read_records, make_batches, load_records, load_cleaned_records, main
