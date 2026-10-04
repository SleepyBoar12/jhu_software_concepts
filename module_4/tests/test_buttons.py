### Test for buttons on page; they must do what they are designed to do.

from unittest.mock import Mock

import pytest

import clean
import flask_app
import load_data
import scrape


class ImmediateThread:
    """Run the background target immediately instead of starting a real thread."""

    def __init__(self, *, target, name, daemon):
        self.target = target
        self.name = name
        self.daemon = daemon

    def start(self):
        self.target()


# Test POST /pull-data returns 200 when not busy and loads mocked scraper rows.
@pytest.mark.buttons
def test_pull_data_when_not_busy(client, monkeypatch, set_pull_state):
    set_pull_state("idle")

    fake_rows = [
        {
            "url": "https://www.thegradcafe.com/result/test-1",
            "program": "Computer Science, Test University",
        }
    ]
    fake_scraper = Mock(
        side_effect=lambda output_directory, page_count: [
            output_directory / "data_1.html"
        ]
    )
    fake_cleaner = Mock(return_value=fake_rows)
    fake_loader = Mock(
        return_value={
            "processed_rows": 1,
            "inserted_rows": 1,
            "updated_rows": 0,
        }
    )

    monkeypatch.setattr(scrape, "scrape_latest_pages", fake_scraper)
    monkeypatch.setattr(clean, "clean_data", fake_cleaner)
    monkeypatch.setattr(load_data, "load_cleaned_records", fake_loader)
    monkeypatch.setattr(flask_app, "Thread", ImmediateThread)

    response = client.post("/pull-data")

    assert response.status_code == 200
    fake_scraper.assert_called_once()
    fake_cleaner.assert_called_once()
    fake_loader.assert_called_once_with(fake_rows)
    assert flask_app.pull_job_status["state"] == "success"


# Test POST /update-analysis returns 200 when not busy.
@pytest.mark.buttons
def test_update_analysis_when_not_busy(
    client,
    monkeypatch,
    set_pull_state,
):
    set_pull_state("idle")
    update_analysis = Mock(return_value=[])
    monkeypatch.setattr(
        flask_app,
        "build_analysis_results",
        update_analysis,
    )

    response = client.post("/update-analysis")

    assert response.status_code == 200
    update_analysis.assert_called_once()


# Test POST /update-analysis returns 409 and performs no update when busy.
@pytest.mark.buttons
def test_update_analysis_when_busy(
    client,
    monkeypatch,
    set_pull_state,
):
    set_pull_state("running")
    update_analysis = Mock()
    monkeypatch.setattr(
        flask_app,
        "build_analysis_results",
        update_analysis,
    )

    response = client.post("/update-analysis")

    assert response.status_code == 409
    update_analysis.assert_not_called()


# Test POST /pull-data returns 409 and starts no worker when busy.
@pytest.mark.buttons
def test_pull_data_when_busy(client, monkeypatch, set_pull_state):
    set_pull_state("running")
    thread = Mock()
    monkeypatch.setattr(flask_app, "Thread", thread)

    response = client.post("/pull-data")

    assert response.status_code == 409
    thread.assert_not_called()
