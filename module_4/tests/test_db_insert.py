"""Test database insertion, input validation, and database configuration."""

from contextlib import nullcontext
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
from unittest.mock import Mock

import dotenv
import psycopg
import pytest
import sqlalchemy
from sqlalchemy.orm import Session

from module_4.src import flask_app, load_data, models, query_data


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
    fake_pull = Mock(
        side_effect=lambda: load_data.load_cleaned_records(fake_rows)
    )

    monkeypatch.setattr(flask_app, "run_pull_pipeline", fake_pull)
    monkeypatch.setattr(flask_app, "Thread", ImmediateThread)

    return fake_pull


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
    fake_pull = configure_fake_pull(monkeypatch)

    assert applicant_count(isolated_database) == 0

    response = client.post("/pull-data")

    assert response.status_code == 200
    fake_pull.assert_called_once_with()
    assert flask_app.pull_job_status["state"] == "success"
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
    fake_pull = configure_fake_pull(monkeypatch)

    first_response = client.post("/pull-data")
    second_response = client.post("/pull-data")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert fake_pull.call_count == 2
    assert flask_app.pull_job_status["state"] == "success"
    assert flask_app.pull_job_status["summary"]["inserted_rows"] == 0
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


@pytest.mark.db
def test_prepare_record_normalizes_input(valid_applicant):
    record = {
        **valid_applicant,
        "program": "  Computer Science, Test University  ",
        "comments": "  ",
        "applicant_status": " Accepted ",
        "gre_v_score": None,
    }

    assert load_data.prepare_record(record, 1) == {
        "program": "Computer Science, Test University",
        "comments": None,
        "date_added": date(2026, 10, 3),
        "url": valid_applicant["url"],
        "status": "Accepted",
        "term": "Fall 2026",
        "us_or_international": "International",
        "gre": Decimal("168"),
        "gre_v": None,
        "degree": "Masters",
        "gpa": Decimal("3.90"),
        "gre_aw": Decimal("4.5"),
        "llm_generated_program": "Computer Science",
        "llm_generated_university": "Test University",
    }


@pytest.mark.db
@pytest.mark.parametrize("value", [None, "", "  ", 42])
def test_required_text_rejects_missing_or_invalid_values(value):
    with pytest.raises(ValueError, match="Line 7 has no valid 'program' value"):
        load_data.required_text({"program": value}, "program", 7)


@pytest.mark.db
@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, None), ("  ", None), (0, "0"), (" padded ", "padded")],
)
def test_optional_text_normalizes_values(value, expected):
    assert load_data.optional_text({"comments": value}, "comments") == expected


@pytest.mark.db
@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, None), ("  ", None), (" 3.90 ", Decimal("3.90")), (0, Decimal(0))],
)
def test_optional_decimal_handles_missing_and_numeric_values(value, expected):
    assert load_data.optional_decimal({"gpa": value}, "gpa", 1) == expected


@pytest.mark.db
@pytest.mark.parametrize("value", ["not a number", "NaN", "Infinity", "-Infinity"])
def test_optional_decimal_rejects_invalid_or_nonfinite_values(value):
    with pytest.raises(ValueError, match="Line 7 has invalid 'gpa'"):
        load_data.optional_decimal({"gpa": value}, "gpa", 7)


@pytest.mark.db
def test_prepare_record_rejects_nonobject():
    with pytest.raises(ValueError, match="Line 3 must contain one JSON object"):
        load_data.prepare_record(["not an object"], 3)


@pytest.mark.db
def test_prepare_record_rejects_invalid_date(valid_applicant):
    valid_applicant["date_added"] = "2026-10-03"
    with pytest.raises(ValueError, match="Line 7 has invalid date_added"):
        load_data.prepare_record(valid_applicant, 7)


@pytest.mark.db
def test_read_records_skips_blank_lines_and_prepares_json(tmp_path, valid_applicant):
    input_file = tmp_path / "applicants.jsonl"
    input_file.write_text("\n" + json.dumps(valid_applicant) + "\n\n", encoding="utf-8")

    records = list(load_data.read_records(input_file))

    assert len(records) == 1
    assert records[0]["date_added"] == date(2026, 10, 3)
    assert records[0]["gpa"] == Decimal("3.90")
    assert records[0]["url"] == valid_applicant["url"]


@pytest.mark.db
def test_read_records_reports_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="Applicant data not found"):
        list(load_data.read_records(tmp_path / "missing.jsonl"))


@pytest.mark.db
def test_read_records_reports_invalid_json_line(tmp_path, valid_applicant):
    input_file = tmp_path / "applicants.jsonl"
    input_file.write_text(json.dumps(valid_applicant) + "\n{invalid}\n", encoding="utf-8")
    records = load_data.read_records(input_file)

    assert next(records)["url"] == valid_applicant["url"]
    with pytest.raises(ValueError, match="Line 2 is not valid JSON"):
        next(records)


@pytest.mark.db
@pytest.mark.parametrize(
    ("records", "size", "expected"),
    [([], 2, []), ([1, 2], 2, [[1, 2]]), ([1, 2, 3], 2, [[1, 2], [3]])],
)
def test_make_batches_handles_empty_full_and_partial_batches(records, size, expected):
    assert list(load_data.make_batches(iter(records), size)) == expected


@pytest.mark.db
def test_load_cleaned_records_batches_and_counts_changes(
    monkeypatch, mock_database, valid_applicant,
):
    connect, connection, cursor = mock_database
    cursor.fetchone.side_effect = [(5,), (6,)]
    cursor.executemany.side_effect = lambda sql, batch: setattr(
        cursor, "rowcount", len(batch),
    )
    monkeypatch.setattr(load_data, "batch_size", 2)
    records = [
        {**valid_applicant, "url": f"https://example.com/{number}"}
        for number in range(3)
    ]

    summary = load_data.load_cleaned_records(iter(records))

    assert summary == {
        "processed_rows": 3,
        "inserted_rows": 1,
        "updated_rows": 2,
        "total_rows": 6,
    }
    connect.assert_called_once()
    batches = [args.args[1] for args in cursor.executemany.call_args_list]
    assert [len(batch) for batch in batches] == [2, 1]
    assert [row["url"] for batch in batches for row in batch] == [
        row["url"] for row in records
    ]
    assert batches[0][0]["gpa"] == Decimal("3.90")
    connection.__exit__.assert_called_once_with(None, None, None)


@pytest.mark.db
@pytest.mark.parametrize("record_count", [0, 1])
def test_load_records_reports_no_changes(mock_database, valid_applicant, record_count):
    _, _, cursor = mock_database
    cursor.fetchone.side_effect = [(7,), (7,)]
    cursor.rowcount = 0

    summary = load_data.load_cleaned_records([valid_applicant] * record_count)

    assert summary == {
        "processed_rows": record_count,
        "inserted_rows": 0,
        "updated_rows": 0,
        "total_rows": 7,
    }
    assert cursor.executemany.call_count == record_count


@pytest.mark.db
def test_load_records_propagates_database_failure(mock_database, valid_applicant):
    _, connection, cursor = mock_database
    cursor.fetchone.return_value = (0,)
    failure = psycopg.Error("Simulated insert failure")
    cursor.executemany.side_effect = failure

    with pytest.raises(psycopg.Error, match="Simulated insert failure"):
        load_data.load_cleaned_records([valid_applicant])

    assert connection.__exit__.call_args.args[:2] == (psycopg.Error, failure)


@pytest.mark.db
def test_loader_command_line_loads_file_and_prints_summary(
    tmp_path, monkeypatch, mock_database, valid_applicant, run_module, capsys,
):
    _, _, cursor = mock_database
    cursor.fetchone.side_effect = [(0,), (1,)]
    cursor.rowcount = 1
    input_file = tmp_path / "applicants.jsonl"
    input_file.write_text(json.dumps(valid_applicant) + "\n", encoding="utf-8")
    original_is_file, original_open = Path.is_file, Path.open
    monkeypatch.setattr(
        Path, "is_file", lambda path: path == load_data.json_file or original_is_file(path),
    )
    monkeypatch.setattr(
        Path, "open",
        lambda path, *args, **kwargs: original_open(
            input_file if path == load_data.json_file else path, *args, **kwargs,
        ),
    )

    run_module(load_data)

    assert capsys.readouterr().out.splitlines() == [
        "Processed 1 JSON records",
        "Inserted 1 database records",
        "Updated 0 database records",
        "The applicants table contains 1 records",
    ]
    cursor.executemany.assert_called_once_with(
        load_data.upsert_sql, [load_data.prepare_record(valid_applicant, 1)],
    )


@pytest.mark.db
@pytest.mark.parametrize(
    "module", [load_data, models, query_data], ids=lambda module: module.__name__,
)
def test_startup_requires_environment_file(module, monkeypatch, run_module):
    env_file = Path(module.__file__).with_name(".env")
    original_is_file = Path.is_file
    monkeypatch.setattr(
        Path, "is_file", lambda path: False if path == env_file else original_is_file(path),
    )

    with pytest.raises(FileNotFoundError, match="Environment file not found"):
        run_module(module, run_name=module.__name__)


@pytest.mark.db
@pytest.mark.parametrize(
    "module", [load_data, query_data], ids=lambda module: module.__name__,
)
def test_startup_reports_missing_environment_variable(module, monkeypatch, run_module):
    monkeypatch.setattr(dotenv, "load_dotenv", Mock(return_value=False))
    monkeypatch.delenv("PGHOST", raising=False)

    with pytest.raises(RuntimeError, match="Missing environment variables:.*PGHOST"):
        run_module(module, run_name=module.__name__)


@pytest.mark.db
def test_applicant_repr_contains_identifying_fields():
    applicant = models.Applicant(p_id=7, program="Computer Science", status="Accepted")
    assert repr(applicant) == "Applicant(p_id=7, program='Computer Science', status='Accepted')"


@pytest.mark.db
def test_model_command_line_checks_connection(
    monkeypatch, fake_pg_environment, run_module, capsys,
):
    session = Mock(spec=Session)
    session.scalar.return_value = 7
    session_factory = Mock(side_effect=lambda: nullcontext(session))
    engine = Mock()
    create_engine = Mock(return_value=engine)
    monkeypatch.setattr(sqlalchemy, "create_engine", create_engine)
    monkeypatch.setattr(sqlalchemy.orm, "sessionmaker", Mock(return_value=session_factory))

    run_module(models)

    assert capsys.readouterr().out.splitlines() == [
        "Successfully connected to PostgreSQL.", "Applicant rows: 7",
    ]
    session.scalar.assert_called_once()
    create_engine.assert_called_once()
    assert create_engine.call_args.args[0].database == "test_applicants"
