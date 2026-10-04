from contextlib import nullcontext
import os
import runpy
import sys
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from module_4.src import flask_app


def pytest_addoption(parser):
    parser.addoption(
        "--require-postgres",
        action="store_true",
        help="Fail database tests instead of skipping when PostgreSQL is unavailable.",
    )


@pytest.fixture
def valid_applicant():
    """Provide a complete input record for loader unit tests."""
    return {
        "program": "Computer Science, Test University",
        "comments": "Example applicant",
        "date_added": "Oct 03, 2026",
        "url": "https://www.thegradcafe.com/result/unit-test-1",
        "applicant_status": "Accepted",
        "program_start": "Fall 2026",
        "student_type": "International",
        "gre_score": "168",
        "gre_v_score": "160",
        "degree": "Masters",
        "gpa": "3.90",
        "gre_aw": "4.5",
        "llm-generated-program": "Computer Science",
        "llm-generated-university": "Test University",
    }


@pytest.fixture
def fake_pg_environment(monkeypatch):
    """Use predictable connection settings in tests with mocked databases."""
    options = {
        "PGHOST": "localhost",
        "PGPORT": "5432",
        "PGDATABASE": "test_applicants",
        "PGUSER": "test_user",
        "PGPASSWORD": "test_password",
    }
    for name, value in options.items():
        monkeypatch.setenv(name, value)
    return options


@pytest.fixture
def mock_database(monkeypatch, fake_pg_environment):
    """Mock the PostgreSQL boundary, including its context managers."""
    connection = MagicMock(spec=psycopg.Connection)
    cursor = MagicMock(spec=psycopg.Cursor)
    connection.__enter__.return_value = connection
    connection.cursor.return_value = cursor
    cursor.__enter__.return_value = cursor
    connect = Mock(return_value=connection)
    monkeypatch.setattr(psycopg, "connect", connect)
    return connect, connection, cursor


@pytest.fixture
def run_module(monkeypatch):
    """Execute a module's real startup code without replacing its functions."""
    def run(module, *, run_name="__main__"):
        # Restore the imported module afterward so later tests keep their state.
        with monkeypatch.context() as patch:
            patch.delitem(sys.modules, module.__name__)
            return runpy.run_module(module.__name__, run_name=run_name)

    return run


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
def isolated_database(monkeypatch, request):
    """Create a temporary PostgreSQL schema and remove it after the test."""
    from module_4.src import load_data

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
        if request.config.getoption("--require-postgres"):
            pytest.fail(f"PostgreSQL is unavailable: {error}", pytrace=False)
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
        if request.config.getoption("--require-postgres"):
            pytest.fail(
                f"Cannot create an isolated PostgreSQL schema: {error}",
                pytrace=False,
            )
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
