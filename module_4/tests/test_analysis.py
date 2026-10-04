"""Test SQL and ORM analysis, query results, and answer formatting."""

from contextlib import nullcontext
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from module_4.src import flask_app, models, orm_queries, query_data
from module_4.src.orm_queries import format_decimal


@pytest.mark.analysis
def test_answer_label_and_percentage_formatting(client, monkeypatch):
    formatted_percentage = format_decimal(Decimal("12.3"), "%")
    assert formatted_percentage == "12.30%"

    fake_results = [
        {
            "number": 1,
            "question": "What percentage of applicants were accepted?",
            "answers": [
                {
                    "label": "Acceptance percentage",
                    "value": formatted_percentage,
                }
            ],
        }
    ]
    monkeypatch.setattr(
        flask_app,
        "build_analysis_results",
        lambda session: fake_results,
    )

    response = client.get("/analysis")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Answer:" in page
    assert "Acceptance percentage" in page
    assert "12.30%" in page


@pytest.mark.analysis
def test_real_analysis_formats_mock_database_results():
    session = Mock(spec=Session)
    session.scalar.side_effect = [
        1200, Decimal("3.75"), 3, 1, 2, 3, 4, 3, 3, 1,
        Decimal("3.98"), 7, Decimal("3.88"),
    ]
    session.execute.return_value.one.return_value = (
        Decimal("3.50"), Decimal("166"), Decimal("160"), Decimal("4.5"),
    )

    results = flask_app.build_analysis_results(session)

    assert [result["number"] for result in results] == list(range(1, 12))
    assert [[answer["value"] for answer in result["answers"]] for result in results] == [
        ["1,200"], ["33.33%"], ["3.50", "166.00", "160.00", "4.50"],
        ["3.75"], ["33.33%"], ["3.98"], ["7"], ["2"], ["3", "1"],
        ["75.00%"], ["3.88"],
    ]


@pytest.mark.analysis
def test_real_analysis_handles_empty_database():
    session = Mock(spec=Session)
    session.scalar.return_value = None
    session.execute.return_value.one.return_value = (None, None, None, None)

    results = flask_app.build_analysis_results(session)

    by_number = {
        result["number"]: [answer["value"] for answer in result["answers"]]
        for result in results
    }
    assert by_number == {
        1: ["0"], 2: ["N/A"], 3: ["N/A"] * 4, 4: ["N/A"], 5: ["N/A"],
        6: ["N/A"], 7: ["0"], 8: ["0"], 9: ["0", "0"], 10: ["N/A"], 11: ["N/A"],
    }


@pytest.mark.analysis
def test_orm_command_line_formats_answers_and_count_difference(
    monkeypatch, run_module, capsys,
):
    session = Mock(spec=Session)
    session.scalar.side_effect = [1234, Decimal("3.85"), 4, 1, 2, 3, 2, 1]
    monkeypatch.setattr(models, "SessionLocal", lambda: nullcontext(session))

    run_module(orm_queries)

    assert capsys.readouterr().out.splitlines() == [
        "1. Fall 2026 applicant count: 1234",
        "4. American Fall 2026 average GPA: 3.85",
        "5. Fall 2025 acceptance percentage: 25.00%",
        "8. Raw-text match count: 2",
        "9. LLM-standardized match count: 3 LLM count minus raw-text count: 1",
        "10. International percentage among accepted NYU master's applicants: 50.00%",
    ]


@pytest.mark.analysis
@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, "N/A"), (Decimal("3.9"), "3.90"), (5, "5"), ("Accepted", "Accepted")],
)
def test_format_value(value, expected):
    assert query_data.format_value(value) == expected


@pytest.mark.analysis
@pytest.mark.parametrize("found", [False, True])
def test_get_applicant_by_url_uses_bound_parameter(found):
    applicant_url = "https://example.com/result/' OR TRUE --"
    row = (
        1, "Computer Science", None, "2026-10-03", applicant_url, "Accepted",
    ) + (None,) * 9
    cursor = Mock(fetchone=Mock(return_value=row if found else None))

    result = query_data.get_applicant_by_url(cursor, applicant_url)

    sql, parameters = cursor.execute.call_args.args
    assert applicant_url not in sql
    assert parameters == (applicant_url,)
    if found:
        assert result["p_id"] == 1
        assert result["url"] == applicant_url
        assert result["status"] == "Accepted"
        assert result["gre"] is None
        assert set(result) == set(query_data.applicant_fields)
    else:
        assert result is None


@pytest.mark.analysis
@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        ([], ["No matching records"]),
        (
            [(Decimal("3.9"), None), (Decimal("4"), 5)],
            ["3.90 | N/A", "4.00 | 5"],
        ),
    ],
)
def test_run_query_prints_columns_and_results(rows, expected, capsys):
    cursor = Mock()
    cursor.description = [SimpleNamespace(name="gpa"), SimpleNamespace(name="gre")]
    cursor.fetchall.return_value = rows

    query_data.run_query(
        cursor, "Applicant scores", "SELECT gpa, gre WHERE status = %s", ("Accepted",),
    )

    lines = capsys.readouterr().out.splitlines()
    assert lines[1:3] == ["Applicant scores", "gpa | gre"]
    assert lines[4:] == expected
    cursor.execute.assert_called_once_with(
        "SELECT gpa, gre WHERE status = %s", ("Accepted",),
    )


@pytest.mark.analysis
def test_query_command_line_runs_all_questions(mock_database, run_module, capsys):
    _, _, cursor = mock_database
    cursor.description = [SimpleNamespace(name="answer")]
    cursor.fetchall.return_value = [(Decimal("12.3"),)]

    run_module(query_data)

    output = capsys.readouterr().out
    headings = [
        line for line in output.splitlines() if line[:1].isdigit() and ". " in line
    ]
    assert [line.split(". ")[0] for line in headings] == [
        "1", "2", "3", "4", "5", "6", "7", "8–9", "10", "11",
    ]
    assert output.count("12.30") == 10
    assert cursor.execute.call_count == 10
    cursor.execute.assert_any_call(
        query_data.question_7_sql, ("Johns Hopkins University", "Computer Science", "Master%"),
    )
