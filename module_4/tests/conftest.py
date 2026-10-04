from contextlib import nullcontext
import os
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

import flask_app


@pytest.fixture
def app(monkeypatch):
    """Create a testable Flask app without connecting to PostgreSQL."""
    fake_results = [
        {
            "number": 1,
            "question": "How many example applicants are there?",
            "answers": [
                {
                    "label": "Example applicants",
                    "value": "5",
                }
            ],
        }
    ]

    monkeypatch.setattr(
        flask_app,
        "SessionLocal",
        lambda: nullcontext(object()),
    )
    monkeypatch.setattr(
        flask_app,
        "build_analysis_results",
        lambda session: fake_results,
    )

    flask_app.app.config.update(TESTING=True)
    return flask_app.app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def set_pull_state(monkeypatch):
    """Set an isolated pull status without changing another test's state."""

    def set_state(state):
        status = {
            "state": state,
            "title": "Test pull status",
            "message": "Test status message",
            "started_at": None,
            "finished_at": None,
            "summary": None,
        }
        monkeypatch.setattr(flask_app, "pull_job_status", status)
        return status

    return set_state


@pytest.fixture
def isolated_database(monkeypatch):
    """Create a temporary PostgreSQL schema and remove it after the test."""
    import load_data

    real_connect = psycopg.connect
    connection_options = {
        "host": os.environ["PGHOST"],
        "port": int(os.environ["PGPORT"]),
        "dbname": os.environ["PGDATABASE"],
        "user": os.environ["PGUSER"],
        "password": os.environ["PGPASSWORD"],
        "connect_timeout": 3,
    }
    schema_name = f"test_applicants_{uuid4().hex}"

    try:
        admin_connection = real_connect(**connection_options)
    except psycopg.OperationalError as error:
        pytest.skip(f"PostgreSQL is unavailable: {error}")

    admin_connection.autocommit = True
    try:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE SCHEMA {}").format(
                    sql.Identifier(schema_name)
                )
            )
    except psycopg.Error as error:
        admin_connection.close()
        pytest.skip(f"Cannot create an isolated PostgreSQL schema: {error}")

    def connect_to_test_schema(*args, **kwargs):
        options = dict(connection_options)
        options.update(kwargs)
        options["options"] = f"-c search_path={schema_name}"
        return real_connect(**options)

    connect_to_test_schema.schema_name = schema_name

    # The loader opens its own connection. Send it to this temporary schema.
    monkeypatch.setattr(load_data.psycopg, "connect", connect_to_test_schema)

    with connect_to_test_schema() as connection:
        with connection.cursor() as cursor:
            cursor.execute(load_data.create_table_sql)

    try:
        yield connect_to_test_schema
    finally:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(
                    sql.Identifier(schema_name)
                )
            )
        admin_connection.close()
