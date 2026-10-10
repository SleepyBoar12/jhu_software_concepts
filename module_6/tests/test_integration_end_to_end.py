### End-to-end tests for pull, update, rendering, and repeated pulls.

from unittest.mock import Mock

import pytest
import re
from bs4 import BeautifulSoup

from module_6.src.web.app import flask_app
from module_6.src.db import load_data


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


@pytest.fixture
def integration_client(isolated_database):
    """Use the real loader and queries through the factory's DATABASE_URL."""
    app = flask_app.create_app(
        {"TESTING": True, "DATABASE_URL": isolated_database.database_url},
        scraper=Mock(), cleaner=Mock(return_value=analysis_rows),
    )
    try:
        yield app.test_client()
    finally:
        app.extensions["database_engine"].dispose()


def configure_fake_pull(client, record_batches):
    """Supply cleaned records while preserving the real loader and analysis."""
    cleaner = Mock(side_effect=record_batches)
    client.application.extensions["etl"]["cleaner"] = cleaner
    return cleaner


def database_counts(connect):
    """Return total rows and distinct URLs from the isolated database."""
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*), COUNT(DISTINCT url) FROM applicants LIMIT 50"
            )
            return cursor.fetchone()


# Pull multiple records, update analysis, and render formatted values.
@pytest.mark.integration
def test_pull_update_and_render_end_to_end(
    integration_client,
    isolated_database,
):
    fake_pull = configure_fake_pull(
        integration_client,
        [analysis_rows],
    )

    before = BeautifulSoup(integration_client.get("/analysis").data, "html.parser")
    assert before.select_one(".analysis-card dd").get_text(strip=True) == "0"
    pull_response = integration_client.post("/pull-data")

    assert pull_response.status_code == 200
    assert pull_response.get_json() == {"ok": True}
    assert database_counts(isolated_database) == (
        len(analysis_rows),
        len(analysis_rows),
    )
    fake_pull.assert_called_once()
    assert integration_client.get("/pull-status").get_json()["state"] == "success"

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
    soup = BeautifulSoup(page, "html.parser")
    assert soup.select_one(".analysis-card dd").get_text(strip=True) == "1"
    percentages = re.findall(r"[^\s]+%", soup.get_text(" ", strip=True))
    assert len(percentages) == 3
    assert all(re.fullmatch(r"\d+\.\d{2}%", value) for value in percentages)
    assert len(soup.select(".answer-label")) == 11


# Overlapping pulls update an existing URL without double counting it.
@pytest.mark.integration
def test_multiple_overlapping_pulls_remain_unique(
    integration_client,
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
        integration_client,
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
    assert integration_client.get("/pull-status").get_json()["state"] == "success"
    assert integration_client.get("/pull-status").get_json()["summary"]["inserted_rows"] == 1
    assert integration_client.get("/pull-status").get_json()["summary"]["updated_rows"] == 1
    assert database_counts(isolated_database) == (3, 3)

    with isolated_database() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT comments FROM applicants WHERE url = %s LIMIT 50",
                (shared_row["url"],),
            )
            saved_comment = cursor.fetchone()[0]

    assert saved_comment == "Updated comment"
