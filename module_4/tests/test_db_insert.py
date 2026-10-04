### Test database insertion, idempotency, and simple queries.

from unittest.mock import Mock

import pytest

import clean
import flask_app
import load_data
import query_data
import scrape


required_fields = {"program", "date_added", "url", "status"}


fake_rows = [
    {
        "program": "Computer Science, Test University",
        "comments": "First test applicant",
        "date_added": "Oct 03, 2026",
        "url": "https://www.thegradcafe.com/result/database-test-1",
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
    },
    {
        "program": "Statistics, Example University",
        "comments": None,
        "date_added": "Oct 03, 2026",
        "url": "https://www.thegradcafe.com/result/database-test-2",
        "applicant_status": "Rejected",
        "program_start": "Fall 2026",
        "student_type": "American",
        "gre_score": None,
        "gre_v_score": None,
        "degree": "PhD",
        "gpa": "3.75",
        "gre_aw": None,
        "llm-generated-program": "Statistics",
        "llm-generated-university": "Example University",
    },
]


class ImmediateThread:
    """Run Flask's background pull immediately during a database test."""

    def __init__(self, *, target, name, daemon):
        self.target = target
        self.name = name
        self.daemon = daemon

    def start(self):
        self.target()


def configure_fake_pull(monkeypatch):
    """Make POST /pull-data process predictable rows without web access."""
    fake_scraper = Mock(
        side_effect=lambda output_directory, page_count: [
            output_directory / "data_1.html"
        ]
    )
    fake_cleaner = Mock(return_value=fake_rows)

    monkeypatch.setattr(scrape, "scrape_latest_pages", fake_scraper)
    monkeypatch.setattr(clean, "clean_data", fake_cleaner)
    monkeypatch.setattr(flask_app, "Thread", ImmediateThread)

    return fake_scraper, fake_cleaner


def applicant_count(connect):
    """Return the number of applicants in the isolated test schema."""
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM applicants")
            return cursor.fetchone()[0]


# Before the pull the table is empty; afterward required fields are populated.
@pytest.mark.db
def test_insert_on_pull(
    client,
    monkeypatch,
    set_pull_state,
    isolated_database,
):
    set_pull_state("idle")
    configure_fake_pull(monkeypatch)

    assert applicant_count(isolated_database) == 0

    response = client.post("/pull-data")

    assert response.status_code == 200
    assert applicant_count(isolated_database) == len(fake_rows)

    with isolated_database() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT program, date_added, url, status FROM applicants"
            )
            inserted_rows = cursor.fetchall()

    assert inserted_rows
    assert all(
        value is not None
        for row in inserted_rows
        for value in row
    )


# Pulling identical rows twice must not create duplicate database rows.
@pytest.mark.db
def test_pull_is_idempotent(
    client,
    monkeypatch,
    set_pull_state,
    isolated_database,
):
    set_pull_state("idle")
    configure_fake_pull(monkeypatch)

    first_response = client.post("/pull-data")
    second_response = client.post("/pull-data")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert applicant_count(isolated_database) == len(fake_rows)

    with isolated_database() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*), COUNT(DISTINCT url) FROM applicants"
            )
            total_rows, unique_urls = cursor.fetchone()

    assert total_rows == unique_urls


# A source query function returns one applicant dictionary with expected keys.
@pytest.mark.db
def test_simple_query_returns_expected_dict(isolated_database):
    load_data.load_cleaned_records([fake_rows[0]])

    with isolated_database() as connection:
        with connection.cursor() as cursor:
            applicant = query_data.get_applicant_by_url(
                cursor,
                fake_rows[0]["url"],
            )

    assert isinstance(applicant, dict)
    assert set(applicant) == set(query_data.applicant_fields)
    assert required_fields <= set(applicant)
    assert all(applicant[field] is not None for field in required_fields)
