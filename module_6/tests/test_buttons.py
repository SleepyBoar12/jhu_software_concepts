"""Exercise the JSON contracts and observable busy state without sleeps."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock

import pytest

from module_6.src.web.app import flask_app


@pytest.mark.buttons
def test_pull_data_when_not_busy(app, client, valid_applicant):
    response = client.post("/pull-data")
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    etl = app.extensions["etl"]
    etl["scraper"].assert_called_once()
    etl["cleaner"].assert_called_once_with(etl["scraper"].call_args.args[0])
    etl["loader"].assert_called_once_with([valid_applicant])
    status = client.get("/pull-status").get_json()
    assert status["state"] == "success"
    assert status["summary"] == etl["loader"].return_value
    assert status["started_at"] and status["finished_at"]


@pytest.mark.buttons
@pytest.mark.parametrize("stage", ["scraper", "cleaner", "loader"])
def test_pull_error_returns_500_and_releases_busy_state(app, client, stage):
    app.extensions["etl"][stage].side_effect = RuntimeError("Simulated failure")
    response = client.post("/pull-data")
    assert response.status_code == 500
    assert response.get_json() == {"ok": False, "error": "Data pull failed"}
    status = client.get("/pull-status").get_json()
    assert status["state"] == "error"
    assert status["summary"] is None
    assert status["finished_at"] is not None
    assert client.post("/update-analysis").status_code == 200


@pytest.mark.buttons
def test_empty_scrape_does_not_call_loader(app, client):
    app.extensions["etl"]["cleaner"].return_value = []
    assert client.post("/pull-data").status_code == 500
    app.extensions["etl"]["loader"].assert_not_called()


@pytest.mark.buttons
def test_update_analysis_when_not_busy(app, client):
    response = client.post("/update-analysis")
    assert response.status_code == 200
    app.extensions["analysis_query"].assert_called_once_with()


@pytest.mark.buttons
@pytest.mark.parametrize("route", ["/pull-data", "/update-analysis"])
def test_busy_requests_do_no_work(app, client, set_pull_state, route):
    set_pull_state("running")
    response = client.post(route)
    assert response.status_code == 409
    assert response.get_json() == {"busy": True}
    app.extensions["analysis_query"].assert_not_called()
    for dependency in app.extensions["etl"].values():
        dependency.assert_not_called()


@pytest.mark.buttons
def test_busy_gating_during_an_actual_pull(app, client):
    started, release = Event(), Event()

    def blocking_scraper(directory):
        started.set()
        assert release.wait(timeout=5), "Test failed to release the fake scraper"

    app.extensions["etl"]["scraper"].side_effect = blocking_scraper
    with ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(lambda: app.test_client().post("/pull-data"))
        try:
            assert started.wait(timeout=5)
            assert client.get("/pull-status").get_json()["state"] == "running"
            for route in ("/pull-data", "/update-analysis"):
                response = client.post(route)
                assert response.status_code == 409
                assert response.get_json() == {"busy": True}
            app.extensions["analysis_query"].assert_not_called()
            app.extensions["etl"]["loader"].assert_not_called()
        finally:
            release.set()
        assert pending.result(timeout=5).get_json() == {"ok": True}
    app.extensions["etl"]["scraper"].assert_called_once()
    app.extensions["etl"]["loader"].assert_called_once()


@pytest.mark.buttons
def test_default_pipeline_wires_real_modules_without_live_io(monkeypatch, valid_applicant):
    from module_2 import clean, scrape
    scraper = Mock()
    cleaner = Mock(return_value=[valid_applicant])
    loader = Mock(return_value={"inserted_rows": 1})
    monkeypatch.setattr(scrape, "scrape_latest_pages", scraper)
    monkeypatch.setattr(clean, "clean_data", cleaner)
    monkeypatch.setattr(flask_app, "load_cleaned_records", loader)
    assert flask_app.run_pull_pipeline() == {"inserted_rows": 1}
    loader.assert_called_once_with([valid_applicant])
    directory = scraper.call_args.args[0]
    cleaner.assert_called_once_with(directory)
    assert not directory.exists()
