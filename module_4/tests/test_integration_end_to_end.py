### End-to-end tests for pull, update, rendering, and repeated pulls.

from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from module_4.src import flask_app, load_data
from module_4.src.models import database_url


def applicant_record(
    identifier,
    program,
    university,
    status,
    term,
    student_type,
    gpa,
    degree="Masters",
    comments=None,
):
    """Build one complete test record in the loader's input format."""
    return {
        "program": f"{program}, {university}",
        "comments": comments,
        "date_added": "Oct 03, 2026",
        "url": f"https://www.thegradcafe.com/result/integration-{identifier}",
        "applicant_status": status,
        "program_start": term,
        "student_type": student_type,
        "gre_score": "165",
        "gre_v_score": "160",
        "degree": degree,
        "gpa": gpa,
        "gre_aw": "4.5",
        "llm-generated-program": program,
        "llm-generated-university": university,
    }


analysis_rows = [
    applicant_record(
        "nyu-accepted",
        "Computer Science",
        "New York University",
        "Accepted",
        "Fall 2025",
        "International",
        "3.80",
    ),
    applicant_record(
        "fall-2025-rejected",
        "Statistics",
        "Example University",
        "Rejected",
        "Fall 2025",
        "American",
        "3.20",
        degree="PhD",
    ),
    applicant_record(
        "jhu-accepted",
        "Computer Science",
        "Johns Hopkins University",
        "Accepted",
        "Fall 2026",
        "American",
        "4.00",
    ),
]


class ImmediateThread:
    """Run the background data pull synchronously during integration tests."""

    def __init__(self, *, target, name, daemon):
        self.target = target
        self.name = name
        self.daemon = daemon

    def start(self):
        self.target()


@pytest.fixture
def integration_client(monkeypatch, isolated_database, set_pull_state):
    """Use the real analysis code against the isolated PostgreSQL schema."""
    test_engine = create_engine(
        database_url,
        connect_args={
            "options": (
                f"-c search_path={isolated_database.schema_name}"
            )
        },
        pool_pre_ping=True,
    )
    test_session = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    monkeypatch.setattr(flask_app, "SessionLocal", test_session)
    monkeypatch.setattr(flask_app, "Thread", ImmediateThread)
    set_pull_state("idle")
    flask_app.app.config.update(TESTING=True)

    try:
        yield flask_app.app.test_client()
    finally:
        test_engine.dispose()


def configure_fake_pull(monkeypatch, record_batches):
    """Supply test records while preserving the real loader and analysis."""
    batches = iter(record_batches)
    fake_pull = Mock(
        side_effect=lambda: load_data.load_cleaned_records(next(batches))
    )

    monkeypatch.setattr(flask_app, "run_pull_pipeline", fake_pull)

    return fake_pull


def database_counts(connect):
    """Return total rows and distinct URLs from the isolated database."""
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*), COUNT(DISTINCT url) FROM applicants"
            )
            return cursor.fetchone()


# Pull multiple records, update analysis, and render formatted values.
@pytest.mark.integration
def test_pull_update_and_render_end_to_end(
    integration_client,
    monkeypatch,
    isolated_database,
):
    fake_pull = configure_fake_pull(
        monkeypatch,
        [analysis_rows],
    )

    pull_response = integration_client.post("/pull-data")

    assert pull_response.status_code == 200
    assert database_counts(isolated_database) == (
        len(analysis_rows),
        len(analysis_rows),
    )
    fake_pull.assert_called_once_with()
    assert flask_app.pull_job_status["state"] == "success"

    update_response = integration_client.post("/update-analysis")
    assert update_response.status_code == 200

    analysis_response = integration_client.get("/analysis")
    page = analysis_response.get_data(as_text=True)

    assert analysis_response.status_code == 200
    assert "Answer:" in page
    assert "33.33%" in page
    assert "50.00%" in page
    assert "100.00%" in page
    assert "3.67" in page
    assert "4.00" in page


# Overlapping pulls update an existing URL without double counting it.
@pytest.mark.integration
def test_multiple_overlapping_pulls_remain_unique(
    integration_client,
    monkeypatch,
    isolated_database,
):
    shared_row = applicant_record(
        "shared",
        "Computer Science",
        "Shared University",
        "Accepted",
        "Fall 2026",
        "American",
        "3.70",
        comments="Original comment",
    )
    first_only_row = applicant_record(
        "first-only",
        "Statistics",
        "First University",
        "Rejected",
        "Fall 2025",
        "International",
        "3.40",
    )
    updated_shared_row = {
        **shared_row,
        "comments": "Updated comment",
    }
    second_only_row = applicant_record(
        "second-only",
        "Mathematics",
        "Second University",
        "Accepted",
        "Fall 2026",
        "International",
        "3.90",
    )
    fake_pull = configure_fake_pull(
        monkeypatch,
        [
            [shared_row, first_only_row],
            [updated_shared_row, second_only_row],
        ],
    )

    first_response = integration_client.post("/pull-data")
    second_response = integration_client.post("/pull-data")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert fake_pull.call_count == 2
    assert flask_app.pull_job_status["state"] == "success"
    assert flask_app.pull_job_status["summary"]["inserted_rows"] == 1
    assert flask_app.pull_job_status["summary"]["updated_rows"] == 1
    assert database_counts(isolated_database) == (3, 3)

    with isolated_database() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT comments FROM applicants WHERE url = %s",
                (shared_row["url"],),
            )
            saved_comment = cursor.fetchone()[0]

    assert saved_comment == "Updated comment"
