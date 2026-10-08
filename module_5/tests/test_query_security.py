"""Verify SQL composition, enforced limits, and malicious input handling."""

import re
from unittest.mock import Mock

from bs4 import BeautifulSoup
from psycopg import sql
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from module_5.src import flask_app, load_data, orm_queries, query_data


@pytest.mark.analysis
@pytest.mark.parametrize("module", [flask_app, orm_queries, query_data],
                         ids=["flask_app", "orm_queries", "query_data"])
@pytest.mark.parametrize("value, expected", [
    (1, 1), (25, 25), (50, 50), (51, 50), (100000, 50),
    (0, 1), (-100, 1), ("30", 30), ("9999", 50),
])
def test_query_limits_are_clamped(module, value, expected):
    assert module.clamp_query_limit(value) == expected


@pytest.mark.analysis
@pytest.mark.parametrize("module", [flask_app, orm_queries, query_data],
                         ids=["flask_app", "orm_queries", "query_data"])
@pytest.mark.parametrize("value", [None, True, 1.5, "", "abc", "1 OR 1=1", "NaN"])
def test_malformed_limits_are_rejected(module, value):
    with pytest.raises(ValueError, match="limit must be an integer"):
        module.clamp_query_limit(value)


@pytest.mark.analysis
def test_dynamic_column_names_are_quoted_and_values_are_bound(monkeypatch):
    """A SQL-looking identifier cannot become another executable statement."""
    column = 'url" FROM applicants; DROP TABLE applicants; --'
    monkeypatch.setattr(query_data, "applicant_fields", (column,))
    cursor = Mock(fetchone=Mock(return_value=None))
    value = "' OR 1=1 --"

    assert query_data.get_applicant_by_url(cursor, value, limit=9999) is None

    stmt, params = cursor.execute.call_args.args
    assert isinstance(stmt, sql.Composed)
    assert sql.Identifier(column).as_string() in stmt.as_string()
    assert value not in stmt.as_string()
    assert params == (value, 50)


@pytest.mark.analysis
def test_run_query_rejects_raw_sql_text():
    cursor = Mock()
    with pytest.raises(TypeError, match="Psycopg SQL object"):
        query_data.run_query(cursor, "Unsafe", "SELECT * FROM applicants")
    cursor.execute.assert_not_called()


@pytest.mark.analysis
def test_all_orm_analysis_queries_have_bound_limits():
    session = Mock(spec=Session)
    session.scalar.return_value = 0
    session.execute.return_value.one.return_value = (None, None, None, None)

    flask_app.build_analysis_results(session, limit=9999)

    calls = [*session.scalar.call_args_list, *session.execute.call_args_list]
    assert len(calls) == 14
    for call in calls:
        compiled = call.args[0].compile(dialect=postgresql.dialect())
        match = re.search(r"LIMIT %\(([^)]+)\)s", str(compiled))
        assert match is not None
        assert compiled.params[match.group(1)] == 50


@pytest.mark.web
@pytest.mark.parametrize("method, path", [("get", "/analysis"), ("post", "/update-analysis")])
@pytest.mark.parametrize("payload", ["' OR 1=1 --", "1; DROP TABLE applicants; --", "NaN", ""])
def test_endpoints_reject_malicious_limits_without_querying(app, client, method, path, payload):
    response = getattr(client, method)(path, query_string={"limit": payload})
    assert response.status_code == 400
    assert response.get_json() == {"error": "limit must be an integer"}
    assert payload not in response.get_data(as_text=True) or payload == ""
    app.extensions["analysis_query"].assert_not_called()


@pytest.mark.web
@pytest.mark.parametrize("value, expected", [("9999", 50), ("0", 1), ("25", 25)])
def test_default_endpoint_passes_clamped_limit(monkeypatch, value, expected):
    factory = Mock(kw={"bind": Mock()})
    monkeypatch.setattr(flask_app, "create_session_factory", Mock(return_value=factory))
    query = Mock(return_value={"analysis_results": []})
    monkeypatch.setattr(flask_app, "query_analysis", query)
    app = flask_app.create_app({"TESTING": True})

    assert app.test_client().get("/analysis", query_string={"limit": value}).status_code == 200
    query.assert_called_once_with(factory, limit=expected)


@pytest.mark.db
@pytest.mark.parametrize("payload", ["' OR 1=1 --", "'; DROP TABLE applicants; --"])
def test_malicious_url_returns_no_other_records(isolated_database, valid_applicant, payload):
    load_data.load_cleaned_records([valid_applicant], database_url=isolated_database.database_url)
    with isolated_database() as connection:
        with connection.cursor() as cursor:
            assert query_data.get_applicant_by_url(cursor, payload) is None
            assert query_data.get_applicant_by_url(cursor, valid_applicant["url"])["url"] == (
                valid_applicant["url"]
            )


@pytest.mark.integration
def test_real_select_is_capped_at_50_and_aggregates_still_count_all(
    isolated_database, valid_applicant, capsys,
):
    records = [
        {**valid_applicant, "url": f"https://example.com/limit-test/{number}"}
        for number in range(60)
    ]
    load_data.load_cleaned_records(records, database_url=isolated_database.database_url)
    stmt = sql.SQL("SELECT {field} FROM {table} ORDER BY {key}").format(
        field=sql.Identifier("url"), table=sql.Identifier("applicants"),
        key=sql.Identifier("p_id"),
    )
    with isolated_database() as connection:
        with connection.cursor() as cursor:
            query_data.run_query(cursor, "URLs", stmt, limit=9999)
            lines = capsys.readouterr().out.splitlines()
            assert len(lines[4:]) == 50
            query_data.run_query(cursor, "Total", query_data.QUESTION_1_SQL, ("Fall 2026",))
            assert capsys.readouterr().out.splitlines()[-1] == "60"


@pytest.mark.integration
@pytest.mark.parametrize("method, path", [("get", "/analysis"), ("post", "/update-analysis")])
def test_real_endpoint_ignores_sql_in_unsupported_filters(
    isolated_database, valid_applicant, method, path,
):
    load_data.load_cleaned_records([valid_applicant], database_url=isolated_database.database_url)
    app = flask_app.create_app({"TESTING": True, "DATABASE_URL": isolated_database.database_url})
    payload = "' OR 1=1; DROP TABLE applicants; --"
    try:
        response = getattr(app.test_client(), method)(
            path, query_string={"url": payload, "columns": payload, "limit": "9999"},
        )
        assert response.status_code == 200
        page = BeautifulSoup(response.data, "html.parser")
        assert len(page.select(".analysis-card")) == 11
        assert page.select_one(".analysis-card dd").get_text(strip=True) == "1"
        assert valid_applicant["url"] not in response.get_data(as_text=True)
        assert payload not in response.get_data(as_text=True)
        with isolated_database() as connection:
            with connection.cursor() as cursor:
                assert query_data.get_applicant_by_url(cursor, valid_applicant["url"]) is not None
    finally:
        app.extensions["database_engine"].dispose()
