from unittest.mock import Mock

import pytest
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

    page = response.get_data(as_text=True)

    # Page contains both the "Pull Data" and "Update Analysis" buttons.
    assert "Pull Data" in page
    assert "Update Analysis" in page

    # Page text includes "Analysis" and at least one "Answer:".
    assert "Analysis" in page
    assert "Answer:" in page


@pytest.mark.web
def test_analysis_database_failure_returns_error_page(client, monkeypatch):
    monkeypatch.setattr(
        flask_app, "SessionLocal", Mock(side_effect=SQLAlchemyError("Database unavailable")),
    )

    response = client.get("/analysis")

    assert response.status_code == 500
    assert "The analysis could not be loaded" in response.get_data(as_text=True)


@pytest.mark.web
def test_flask_command_line_starts_server(monkeypatch, run_module):
    run_server = Mock()
    monkeypatch.setattr(Flask, "run", run_server)

    run_module(flask_app)

    run_server.assert_called_once_with()
