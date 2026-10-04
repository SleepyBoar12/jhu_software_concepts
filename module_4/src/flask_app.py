"""Display live PostgreSQL analysis results in a Flask webpage."""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock, Thread

from flask import Flask, jsonify, render_template
from sqlalchemy import Numeric, and_, cast, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models import Applicant, SessionLocal
from orm_queries import (
    format_decimal,
    question_1,
    question_4,
    question_5,
    question_8,
    question_9,
    question_10,
)


app = Flask(__name__)
pull_status_lock = Lock()
pull_job_status = {
    "state": "idle",
    "title": "No data pull is running",
    "message": "The analysis is using the current PostgreSQL data.",
    "started_at": None,
    "finished_at": None,
    "summary": None,
}

def run_pull_pipeline():
    """Scrape, clean, and upsert the latest GradCafe records."""

    # Import scraping dependencies only after the user presses Pull Data.
    from clean import clean_data
    from load_data import load_cleaned_records
    from scrape import scrape_latest_pages

    # Temporary HTML is removed automatically after the records are cleaned.
    with TemporaryDirectory(prefix="gradcafe_pull_") as temporary_directory:
        temporary_path = Path(temporary_directory)
        saved_pages = scrape_latest_pages(temporary_path, page_count=5)
        cleaned_records = clean_data(temporary_path)

    if not cleaned_records:
        raise RuntimeError("The scraped pages contained no applicant records")

    summary = load_cleaned_records(cleaned_records)
    summary["scraped_pages"] = len(saved_pages)
    return summary


def get_pull_status():
    """Return a copy of the shared background-pull status."""

    with pull_status_lock:
        status = dict(pull_job_status)
        if status["summary"] is not None:
            status["summary"] = dict(status["summary"])
        return status


def update_pull_status(**changes):
    """Update the background-pull status while holding its lock."""

    with pull_status_lock:
        pull_job_status.update(changes)


def pull_data_worker():
    """Run the slow scraping pipeline without blocking Flask page requests."""

    try:
        summary = run_pull_pipeline()
    except Exception:
        app.logger.exception("Unable to pull new GradCafe data")
        update_pull_status(
            state="error",
            title="The data pull did not finish",
            message=(
                "Check the Flask terminal and confirm that Chrome, the "
                "internet connection, and PostgreSQL are available."
            ),
            finished_at=datetime.now().astimezone().isoformat(),
            summary=None,
        )
        return

    update_pull_status(
        state="success",
        title="GradCafe data pull completed",
        message=(
            f"Checked {summary['scraped_pages']} pages and processed "
            f"{summary['processed_rows']} records. Added "
            f"{summary['inserted_rows']} new records and refreshed "
            f"{summary['updated_rows']} existing records. Select Update "
            f"Analysis to display the newly committed data."
        ),
        finished_at=datetime.now().astimezone().isoformat(),
        summary=summary,
    )


def calculate_percentage(part_count, total_count):
    """Return a percentage rounded to two places or None for no rows."""

    if total_count == 0:
        return None

    return round(100 * part_count / total_count, 2)


def rounded_average(column):
    """Create a PostgreSQL average expression rounded to two places."""

    return func.round(cast(func.avg(column), Numeric), 2)


def question_2(session: Session):
    """Find the international percentage among classified applicants."""

    classified_statement = select(func.count(Applicant.p_id)).where(
        Applicant.us_or_international.is_not(None)
    )
    international_statement = select(func.count(Applicant.p_id)).where(
        Applicant.us_or_international == "International"
    )

    classified_count = session.scalar(classified_statement) or 0
    international_count = session.scalar(international_statement) or 0
    return calculate_percentage(international_count, classified_count)


def question_3(session: Session):
    """Find the average of each available GPA and GRE measurement."""

    statement = select(
        rounded_average(Applicant.gpa),
        rounded_average(Applicant.gre),
        rounded_average(Applicant.gre_v),
        rounded_average(Applicant.gre_aw),
    )
    average_gpa, average_gre, average_gre_v, average_gre_aw = (
        session.execute(statement).one()
    )

    return {
        "gpa": average_gpa,
        "gre": average_gre,
        "gre_v": average_gre_v,
        "gre_aw": average_gre_aw,
    }


def question_6(session: Session):
    """Find the average GPA of accepted Fall 2026 applicants."""

    statement = select(rounded_average(Applicant.gpa)).where(
        and_(
            Applicant.term == "Fall 2026",
            Applicant.status == "Accepted",
            Applicant.gpa.is_not(None),
        )
    )
    return session.scalar(statement)


def question_7(session: Session) -> int:
    """Count Johns Hopkins Computer Science master's applicants."""

    statement = select(func.count(Applicant.p_id)).where(
        and_(
            func.lower(Applicant.llm_generated_university)
            == "johns hopkins university",
            func.lower(Applicant.llm_generated_program)
            == "computer science",
            Applicant.degree.ilike("Master%"),
        )
    )
    return session.scalar(statement) or 0


def question_11(session: Session):
    """Find the average GPA of accepted Johns Hopkins master's applicants."""

    statement = select(rounded_average(Applicant.gpa)).where(
        and_(
            Applicant.status == "Accepted",
            func.lower(Applicant.llm_generated_university)
            == "johns hopkins university",
            Applicant.degree.ilike("Master%"),
            Applicant.gpa.is_not(None),
        )
    )
    return session.scalar(statement)


def build_analysis_results(session: Session):
    """Run every analysis and organize the answers for the HTML template."""

    # Reuse the questions that already exist in orm_queries.py.
    fall_2026_count = question_1(session)
    american_average_gpa = question_4(session)
    fall_2025_acceptance_percentage = question_5(session)
    raw_text_count = question_8(session)
    llm_standardized_count = question_9(session)
    nyu_international_percentage = question_10(session)

    # Run only the missing questions defined in this Flask module.
    international_percentage = question_2(session)
    averages = question_3(session)
    accepted_average_gpa = question_6(session)
    johns_hopkins_count = question_7(session)
    johns_hopkins_average_gpa = question_11(session)

    return [
        {
            "number": 1,
            "question": "How many entries are from applicants who applied for Fall 2026?",
            "answers": [
                {"label": "Fall 2026 entries", "value": f"{fall_2026_count:,}"}
            ],
        },
        {
            "number": 2,
            "question": (
                "Among entries that provided a nationality classification, "
                "what percentage are international students?"
            ),
            "answers": [
                {
                    "label": "International applicants",
                    "value": format_decimal(international_percentage, "%"),
                }
            ],
        },
        {
            "number": 3,
            "question": (
                "What are the average GPA, GRE Quantitative, GRE Verbal, and "
                "GRE Analytical Writing scores?"
            ),
            "answers": [
                {"label": "GPA", "value": format_decimal(averages["gpa"])},
                {
                    "label": "GRE Quantitative",
                    "value": format_decimal(averages["gre"]),
                },
                {
                    "label": "GRE Verbal",
                    "value": format_decimal(averages["gre_v"]),
                },
                {
                    "label": "GRE Writing",
                    "value": format_decimal(averages["gre_aw"]),
                },
            ],
            "note": "Each average ignores rows where that measurement is SQL NULL.",
        },
        {
            "number": 4,
            "question": "What is the average GPA of American Fall 2026 applicants?",
            "answers": [
                {
                    "label": "Average GPA",
                    "value": format_decimal(american_average_gpa),
                }
            ],
        },
        {
            "number": 5,
            "question": "What percentage of Fall 2025 entries are acceptances?",
            "answers": [
                {
                    "label": "Acceptance percentage",
                    "value": format_decimal(fall_2025_acceptance_percentage, "%"),
                }
            ],
        },
        {
            "number": 6,
            "question": "What is the average GPA of accepted Fall 2026 applicants?",
            "answers": [
                {
                    "label": "Average GPA",
                    "value": format_decimal(accepted_average_gpa),
                }
            ],
        },
        {
            "number": 7,
            "question": (
                "How many entries are for the Johns Hopkins University "
                "Computer Science master's program?"
            ),
            "answers": [
                {
                    "label": "Matching entries",
                    "value": f"{johns_hopkins_count:,}",
                }
            ],
        },
        {
            "number": 8,
            "question": (
                "How many accepted Fall 2026 Computer Science PhD applicants "
                "matched Georgetown, MIT, Stanford, or Carnegie Mellon in "
                "the raw program text?"
            ),
            "answers": [
                {"label": "Raw-text matches", "value": f"{raw_text_count:,}"}
            ],
        },
        {
            "number": 9,
            "question": (
                "Using the LLM-generated university and program terms, what "
                "is the matching count and its difference from Question 8?"
            ),
            "answers": [
                {
                    "label": "LLM-standardized matches",
                    "value": f"{llm_standardized_count:,}",
                },
                {
                    "label": "LLM minus raw-text",
                    "value": f"{llm_standardized_count - raw_text_count:,}",
                },
            ],
            "note": "Question 9 requires an exact standardized program match.",
        },
        {
            "number": 10,
            "question": (
                "What percentage of accepted NYU master's applicants are "
                "international?"
            ),
            "answers": [
                {
                    "label": "International applicants",
                    "value": format_decimal(nyu_international_percentage, "%"),
                }
            ],
        },
        {
            "number": 11,
            "question": (
                "What is the average GPA of accepted Johns Hopkins master's "
                "applicants?"
            ),
            "answers": [
                {
                    "label": "Average GPA",
                    "value": format_decimal(johns_hopkins_average_gpa),
                }
            ],
        },
    ]


@app.post("/pull-data")
def pull_data():
    """Start one background data pull and return to the page immediately."""

    with pull_status_lock:
        if pull_job_status["state"] == "running":
            return "A data pull is already in progress.", 409

        pull_job_status.update(
            state="running",
            title="Retrieving new GradCafe data",
            message=(
                "The newest pages are being scraped, cleaned, and added to "
                "PostgreSQL. You can update the analysis while this continues."
            ),
            started_at=datetime.now().astimezone().isoformat(),
            finished_at=None,
            summary=None,
        )

    # A daemon thread lets Flask keep serving analysis requests concurrently.
    worker = Thread(
        target=pull_data_worker,
        name="gradcafe-pull-data",
        daemon=True,
    )
    worker.start()
    return index()


@app.get("/pull-status")
def pull_status_endpoint():
    """Provide live pull progress for the webpage's status display."""

    return jsonify(get_pull_status())


@app.get("/analysis")
@app.get("/")
def index():
    """Query PostgreSQL and render a fresh analysis page on every request."""

    try:
        with SessionLocal() as session:
            analysis_results = build_analysis_results(session)
    except SQLAlchemyError:
        app.logger.exception("Unable to load applicant analysis")
        return render_template(
            "index.html",
            analysis_results=[],
            generated_at=None,
            pull_status=get_pull_status(),
            error=(
                "The analysis could not be loaded. Confirm that PostgreSQL "
                "is running and that the .env credentials are correct."
            ),
        ), 500

    generated_at = datetime.now().astimezone()
    return render_template(
        "index.html",
        analysis_results=analysis_results,
        generated_at=generated_at,
        pull_status=get_pull_status(),
        error=None,
    )


@app.post("/update-analysis")
def update_analysis():
    """Refresh the analysis unless a data pull is still running."""

    with pull_status_lock:
        if pull_job_status["state"] == "running":
            return "Analysis cannot update while a data pull is running.", 409

    return index()


if __name__ == "__main__":
    app.run()
