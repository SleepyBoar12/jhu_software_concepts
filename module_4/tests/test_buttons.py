### Test for buttons on page; they must do what they are designed to do.

from unittest.mock import Mock

import pytest

from module_4.src import flask_app


class ImmediateThread:
    """Run the background target immediately instead of starting a real thread."""

    def __init__(self, *, target, name, daemon):
        self.target = target
        self.name = name
        self.daemon = daemon

    def start(self):
        self.target()


# Test POST /pull-data returns 200 when not busy and reports a mocked pull.
@pytest.mark.buttons
def test_pull_data_when_not_busy(client, monkeypatch, set_pull_state):
    set_pull_state("idle")

    fake_pull = Mock(
        return_value={
            "processed_rows": 1,
            "inserted_rows": 1,
            "updated_rows": 0,
        }
    )

    monkeypatch.setattr(flask_app, "run_pull_pipeline", fake_pull)
    monkeypatch.setattr(flask_app, "Thread", ImmediateThread)

    response = client.post("/pull-data")

    assert response.status_code == 200
    fake_pull.assert_called_once_with()
    assert flask_app.pull_job_status["state"] == "success"
    assert flask_app.pull_job_status["summary"] == fake_pull.return_value
    assert "Processed 1 records" in flask_app.pull_job_status["message"]


# A pull without the test replacement reports the missing live collector.
@pytest.mark.buttons
def test_pull_data_without_live_collection(client, monkeypatch, set_pull_state):
    set_pull_state("idle")
    monkeypatch.setattr(flask_app, "Thread", ImmediateThread)

    response = client.post("/pull-data")

    assert response.status_code == 200
    status = client.get("/pull-status").get_json()
    assert status["state"] == "error"
    assert status["summary"] is None
    assert status["finished_at"] is not None
    assert "Live data collection is not included" in status["message"]


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
