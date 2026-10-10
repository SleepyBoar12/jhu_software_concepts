# Module 6 multi-service scaffold

This baseline runs Flask, a background worker, PostgreSQL, and RabbitMQ.
The original analysis and synchronous Pull Data behavior are preserved. The
new `/jobs` endpoint demonstrates queued work. Incremental scraping is an
explicit stand-in that returns no new records until implemented.

## Layout

```text
module_6/
    docker-compose.yml
    setup.py
    README.md
    requirements.txt
    docs/
    tests/
    src/
        messaging.py
        web/
            Dockerfile
            requirements.txt
            run.py
            publisher.py
            app/
                flask_app.py
                templates/
                static/
        worker/
            Dockerfile
            requirements.txt
            consumer.py
            etl/
                incremental_scraper.py
                query_data.py
                orm_queries.py
        db/
            config.py
            init.sql
            models.py
            load_data.py
        data/
            applicant_data.json
```

Package directories also contain `__init__.py`. Repository-wide workflows,
`.gitignore`, and `.dockerignore` live at the repository root. The existing
Module 2 scraper and cleaner remain shared dependencies for the original
synchronous Flask pull pipeline; both Docker builds include their Python files.

Both service Dockerfiles use `python:3.14-slim` to match the project's Python
3.14 requirement. The slim image includes fewer operating-system packages;
the current dependencies install without additional system build tools. Each
service runs as `appuser` with UID/GID 1000, with an owned application directory
and home directory.

Compose builds from the repository root so the images can include the shared
database, messaging, and Module 2 code. The startup commands use `python -m`
to resolve package-relative imports. `src/web/run.py` initializes the schema
and starts Flask on `0.0.0.0:8080`; `src/web/app/flask_app.py` contains the Flask
application factory and routes. The worker starts with
`python -m module_6.src.worker.consumer`.

## Start all four services

From the repository root:

```bash
cd module_6
docker compose config --quiet
docker compose up --build -d --wait
docker compose ps
```

Open [the analysis page](http://localhost:8080/analysis). The web entrypoint
binds to `0.0.0.0:8080` and creates the applicants table if needed. It does not
automatically import the full dataset. Compose waits for database and broker
health before starting web and worker. All four services join Compose's
project-specific default bridge network.

PostgreSQL runs `src/db/init.sql` when initializing an empty database volume,
so the schema exists even when web is not running. The Python loader reads the
same SQL file and can also create the table in an existing local database.
The initialization script is not a migration system for future schema changes.

| Service | Host port | Container port |
|---|---:|---:|
| Flask web | 8080 | 8080 |
| PostgreSQL | 5433 | 5432 |
| RabbitMQ AMQP | 5672 | 5672 |
| RabbitMQ management UI | 15672 | 15672 |

The database host port is 5433 to coexist with a local PostgreSQL server on
5432. Inside Docker, the database hostname is `db`, and the broker hostname is
`rabbitmq`. The default development database role is `gradcafe`, with password
`gradcafe-local`; RabbitMQ uses the same default username and password.
Optional overrides are documented in `.env.example`. Place Compose overrides
in `module_6/.env`; local Python database settings belong in `src/.env`.

The named `db_data` and `rabbitmq_data` volumes preserve database and broker
data. The named `applicant_data` volume mounts `/app/module_6/src/data` in both
web and worker, sharing the JSON data folder. On its first use, Docker copies
the bundled applicant file into the empty volume. Container recreation retains
that volume's contents; rebuilding images does not overwrite an existing data
volume. `docker compose down` stops and removes containers while retaining
these volumes.

To start one application service with its database and broker dependencies:

```bash
docker compose up --build -d --wait web
# Or, instead of web:
docker compose up --build -d --wait worker
```

Web can serve pages and enqueue jobs while worker is stopped. Worker can
consume jobs and use the database while web is stopped. These commands leave
any already-running services running.

## Demonstrate queued work

```bash
curl -X POST http://localhost:8080/jobs \
  -H 'Content-Type: application/json' \
  -d '{"task":"noop"}'
docker compose logs worker
```

The response is HTTP 202 with `{"queued":true}`. The worker logs completion
and acknowledges the message after processing. Both services declare the same
durable exchange and queue. The publisher uses persistent messages
(`delivery_mode=2`) and publisher confirms; the worker uses manual acknowledgements
and `prefetch_count=1`. Malformed jobs are rejected, and database failures are
requeued.

`{"task":"scrape"}` invokes the incremental scraper stand-in and the loader
with an empty list. It inserts no fake records. Implement real incremental
scraping in `src/worker/etl/incremental_scraper.py` when ready. The existing
`/pull-data` endpoint still uses the original synchronous pipeline, which
requires Chrome for live scraping. The scaffold images do not install Chrome.

## Load applicant data and run analysis

The existing LLM-cleaned file was renamed to `src/data/applicant_data.json`
without changing its contents. It uses JSON Lines: one object per line.

```bash
docker compose exec worker python -m module_6.src.db.load_data
docker compose exec worker python -m module_6.src.worker.etl.query_data
```

The loader resolves its input path relative to its source file, independently
of the working directory. For a JSON array, use `json.loads` and pass the
records to `load_cleaned_records` instead.

## Local Python development and checks

Use Python 3.14. From `module_6`:

```bash
python3.14 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
python -m pip check
pylint src
pytest tests --require-postgres
```

Configure a local test database in `src/.env` or `DATABASE_URL`. Tests use
isolated schemas and retain the 100% statement coverage requirement. Tests
without `--require-postgres` may skip database checks when PostgreSQL is
unavailable. RabbitMQ unit tests use a mocked broker and require no running
RabbitMQ server.

To run Flask locally with database configuration in place:

```bash
python -m module_6.src.web.run
```

`src/db/config.py` supplies database settings to both services; the models and
loader do not import Flask. The web and worker requirements files specify
runtime dependencies. Root `requirements.txt` additionally pins lint, test,
and documentation dependencies.

Build documentation with:

```bash
python -m sphinx -b html -W --keep-going docs/source docs/build/html
```

The root `.github/workflows/module_6.yml` validates Compose, lint, tests, and
documentation for this module. The existing workflows for earlier modules
remain available.

## Container images and registries

Compose builds local images named `jhu-gradcafe-web:module6` and
`jhu-gradcafe-worker:module6`. These are stand-in image names and have not been
published. After publishing, add their actual registry links here and update
the Compose `image` values. For example, a future registry reference could be
`ghcr.io/<owner>/jhu-gradcafe-web:module6`.

The current base-image registry links are:

- [Python](https://hub.docker.com/_/python) (`python:3.14-slim`)
- [PostgreSQL](https://hub.docker.com/_/postgres) (`postgres:16-alpine`)
- [RabbitMQ](https://hub.docker.com/_/rabbitmq) (`rabbitmq:4-management-alpine`)
