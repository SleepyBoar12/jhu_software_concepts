### Test labels and rounding for rendered analysis.

from decimal import Decimal
import pytest
import flask_app
from orm_queries import format_decimal


# Test that the page includes an Answer label and a two-decimal percentage.
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
