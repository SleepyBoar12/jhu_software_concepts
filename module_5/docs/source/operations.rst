Operational notes
=====================

Busy-state policy
---------------------

Each ``create_app`` call owns a lock and a status dictionary. A pull atomically
claims the idle state, then performs ETL in its request thread. Concurrent
``POST /pull-data`` and ``POST /update-analysis`` requests receive HTTP 409
with ``{"busy": true}`` and perform no ETL or query work. ``GET /pull-status``
remains available. ``GET /analysis`` may read the last committed data.

A successful pull returns HTTP 200 with ``{"ok": true}`` after the loader
commits. A failed pull returns HTTP 500 with ``{"ok": false, "error":
"Data pull failed"}``, records an error status, and releases the busy state.
The browser submits with fetch and remains on the analysis page. After a
successful pull, Update Analysis displays the newly committed results.

The lock is process-local. Run a single application process with multiple
request threads so status and busy gating are shared by all requests. A
multi-process deployment would need a shared job state and lock before using
this policy. Live scrapes can be slow; configure the server/proxy request timeout
accordingly. Tests inject immediate functions or event-controlled fakes.

Idempotency and uniqueness
------------------------------

``applicants.url`` is the unique source key, and ``p_id`` is the generated
identity primary key. Repeated identical input does not add or change rows.
A changed record with an existing URL updates that row. Missing incoming
LLM labels preserve previously stored labels. PostgreSQL enforces uniqueness.

The table definition and upsert SQL preserve Module 3. Required non-null
fields are ``p_id``, ``program``, ``date_added``, ``url``, and ``status``.
Other fields retain their prior nullability and types. Tests compare the table
SQL to Module 3 and inspect the actual PostgreSQL columns.

Transactions and failures
-----------------------------

All batches in one pull use one transaction. Validation errors, database
constraint failures, and other loader exceptions roll back every batch.
There are no intermediate commits. A successful response therefore means
records have committed, and a loader failure leaves no partial rows.

Custom injected loaders must honor the same transaction contract. Status
summaries include processed, inserted, updated, and total row counts. These
counts describe one serialized application pull; external concurrent writers
can affect before/after totals.

Configuration and maintenance
---------------------------------

Keep credentials in ``DATABASE_URL`` or the optional gitignored dotenv file.
Use an explicit factory configuration for a test or alternative database.
Dispose ``app.extensions["database_engine"]`` when retiring an app instance.
The schema fixture handles this for integration tests and removes its test
schema after each test. See :doc:`overview` for troubleshooting and
:doc:`publishing` for Read the Docs updates.
