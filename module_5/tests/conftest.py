"""Offline test doubles and isolated real PostgreSQL schemas."""

import runpy
import sys
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from module_5.src import flask_app
from module_5.src.flask_app import connection_string, get_database_url


ALLOWED_MARKERS = {"web", "buttons", "analysis", "db", "integration"}


def pytest_addoption(parser):
    parser.addoption(
        "--require-postgres", action="store_true",
        help="Fail database tests instead of skipping when PostgreSQL is unavailable.",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    """Reject unmarked tests before pytest applies marker deselection."""
    unmarked = [item.nodeid for item in items
                if not ALLOWED_MARKERS.intersection(m.name for m in item.iter_markers())]
    if unmarked:
        raise pytest.UsageError("Tests require a category marker: " + ", ".join(unmarked))


@pytest.fixture(autouse=True)
def no_live_scraping(monkeypatch):
    """Make accidental HTTP requests or browser startup fail immediately."""
    import urllib.request
    import urllib3
    from selenium import webdriver

    def forbidden(*args, **kwargs):
        raise AssertionError("Live HTTP requests and browser startup are forbidden in tests")

    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(urllib3.PoolManager, "request", forbidden)
    monkeypatch.setattr(webdriver, "Chrome", forbidden)


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
    """Provide a credential-free URI for tests whose connections are mocked."""
    url = "postgresql://localhost/test_applicants"
    monkeypatch.setenv("DATABASE_URL", url)
    return url


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
    """Execute startup code, then restore the imported module."""
    def run(module, *, run_name="__main__"):
        with monkeypatch.context() as patch:
            patch.delitem(sys.modules, module.__name__)
            return runpy.run_module(module.__name__, run_name=run_name)
    return run


@pytest.fixture
def app(valid_applicant):
    """Build a fresh app using injected ETL and query functions."""
    return flask_app.create_app(
        {"TESTING": True},
        scraper=Mock(return_value=[]),
        cleaner=Mock(return_value=[valid_applicant]),
        loader=Mock(return_value={"processed_rows": 1, "inserted_rows": 1,
                                  "updated_rows": 0, "total_rows": 1}),
        query=Mock(return_value={"analysis_results": [{
            "number": 1, "question": "How many example applicants are there?",
            "answers": [{"label": "Example applicants", "value": "5"}],
        }]}),
    )


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def set_pull_state(app):
    """Expose the current app's busy state without timing assumptions."""
    def set_state(state):
        app.extensions["pull_state"]["status"]["state"] = state
        return app.extensions["pull_state"]["status"]
    return set_state


@pytest.fixture
def isolated_database(request):
    """Use a unique PostgreSQL schema; never modify the application's rows."""
    try:
        database_url = get_database_url()
        connection_uri = connection_string(database_url)
        admin_connection = psycopg.connect(connection_uri, connect_timeout=3)
    except (RuntimeError, psycopg.OperationalError) as error:
        if request.config.getoption("--require-postgres"):
            pytest.fail(f"PostgreSQL is unavailable: {error}", pytrace=False)
        pytest.skip("PostgreSQL is unavailable; use --require-postgres to require it")

    schema_name = f"test_applicants_{uuid4().hex}"
    admin_connection.autocommit = True
    try:
        with admin_connection.cursor() as cursor:
            stmt = sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name))
            cursor.execute(stmt)
    except psycopg.Error:
        admin_connection.close()
        raise

    test_url = database_url.update_query_dict({"options": f"-c search_path={schema_name}"})
    test_uri = connection_string(test_url)

    def connect_to_test_schema():
        return psycopg.connect(test_uri)

    connect_to_test_schema.schema_name = schema_name
    connect_to_test_schema.database_url = test_uri
    try:
        from module_5.src.load_data import CREATE_TABLE_SQL
        with connect_to_test_schema() as connection:
            connection.execute(CREATE_TABLE_SQL)
        yield connect_to_test_schema
    finally:
        with admin_connection.cursor() as cursor:
            stmt = sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema_name))
            cursor.execute(stmt)
        admin_connection.close()
