from unittest.mock import Mock

import pytest
from bs4 import BeautifulSoup
from flask import Flask
from sqlalchemy.exc import SQLAlchemyError

from module_4.src import flask_app


# Test that a Flask app is created and configured for testing.
@pytest.mark.web
def test_flask(app):
    assert isinstance(app, Flask)
    assert app.config["TESTING"] is True


# Test that the Flask app is created with all required routes.
@pytest.mark.web
def test_routes(app):
    required_routes = {
        ("/", "GET"),
        ("/analysis", "GET"),
        ("/pull-data", "POST"),
        ("/pull-status", "GET"),
        ("/update-analysis", "POST"),
    }

    actual_routes = {
        (rule.rule, method)
        for rule in app.url_map.iter_rules()
        for method in rule.methods
        if method in {"GET", "POST"}
    }

    missing_routes = required_routes - actual_routes
    assert not missing_routes, f"Missing routes: {missing_routes}"


# Test GET /analysis (status 200).
@pytest.mark.web
def test_render(client):
    response = client.get("/analysis")

    assert response.status_code == 200

    page = BeautifulSoup(response.data, "html.parser")
    assert "Analysis" in page.title.get_text()
    assert page.select_one('[data-testid="pull-data-btn"]').get_text(strip=True) == "Pull Data"
    assert page.select_one('[data-testid="update-analysis-btn"]').get_text(strip=True) == "Update Analysis"
    assert page.select_one(".answer-label").get_text(strip=True) == "Answer:"


@pytest.mark.web
def test_analysis_database_failure_returns_error_page(app, client):
    app.extensions["analysis_query"].side_effect = SQLAlchemyError("Database unavailable")

    response = client.get("/analysis")

    assert response.status_code == 500
    assert "The analysis could not be loaded" in response.get_data(as_text=True)


@pytest.mark.web
def test_flask_command_line_starts_server(monkeypatch, run_module, fake_pg_environment):
    run_server = Mock()
    monkeypatch.setattr(Flask, "run", run_server)

    run_module(flask_app)

    run_server.assert_called_once_with()


@pytest.mark.web
def test_app_factory_isolates_configuration_and_busy_state(app):
    other = flask_app.create_app({"TESTING": True}, query=lambda: {"analysis_results": []})
    app.extensions["pull_state"]["status"]["state"] = "running"
    assert other.test_client().get("/pull-status").get_json()["state"] == "idle"
    assert other.test_client().post("/update-analysis").status_code == 200
    with app.app_context():
        flask_app.update_pull_status(summary={"inserted_rows": 2})
        snapshot = flask_app.get_pull_status()
        snapshot["summary"]["inserted_rows"] = 99
        assert flask_app.get_pull_status()["summary"]["inserted_rows"] == 2


@pytest.mark.web
def test_factory_default_loader_uses_configured_database(monkeypatch, valid_applicant):
    url = "postgresql://localhost/overridden"
    loader = Mock(return_value={"processed_rows": 1, "inserted_rows": 1, "updated_rows": 0})
    monkeypatch.setattr(flask_app, "load_cleaned_records", loader)
    app = flask_app.create_app(
        {"TESTING": True, "DATABASE_URL": url},
        query=lambda: {"analysis_results": []},
        scraper=Mock(), cleaner=lambda directory: [valid_applicant],
    )
    assert app.test_client().post("/pull-data").get_json() == {"ok": True}
    loader.assert_called_once_with([valid_applicant], database_url=url)
