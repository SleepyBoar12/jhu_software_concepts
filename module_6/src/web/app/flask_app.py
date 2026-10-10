"""Configure PostgreSQL connections and display analysis in a Flask webpage."""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock

import pika
from flask import Flask, current_app, jsonify, render_template, request
from sqlalchemy import Numeric, and_, cast, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import count

from module_2 import clean, scrape


from ...db.models import Applicant, create_session_factory
from ...db.load_data import load_cleaned_records
from ...worker.etl.orm_queries import collect_orm_results, format_decimal
from ..publisher import publish_job

MAX_QUERY_LIMIT = 50


def clamp_query_limit(limit=MAX_QUERY_LIMIT):
    """Accept an integer limit, clamp it to 1–50, and reject malformed input."""
    # Keep validation local to each module; the same tests cover all copies.
    # pylint: disable=duplicate-code
    if isinstance(limit, bool) or not isinstance(limit, (int, str)):
        raise ValueError("limit must be an integer")
    try:
        number = int(limit)
    except ValueError as error:
        raise ValueError("limit must be an integer") from error
    return max(1, min(number, MAX_QUERY_LIMIT))


def run_pull_pipeline(*, scraper=None, cleaner=None, loader=None):
    """Scrape, clean, and load records, with replaceable ETL dependencies.

    The scraper accepts an output directory; the cleaner reads that directory;
    the loader accepts cleaned dictionaries and returns a committed summary.
    Temporary HTML is removed after success or failure.
    """
    if scraper is None:
        scraper = scrape.scrape_latest_pages
    if cleaner is None:
        cleaner = clean.clean_data
    if loader is None:
        loader = load_cleaned_records
    with TemporaryDirectory(prefix="gradcafe_pull_") as directory:
        scraper(Path(directory))
        records = cleaner(Path(directory))
        if not records:
            raise ValueError("The collected pages contained no applicant records")
        return loader(records)


def get_pull_status():
    """Return an isolated snapshot of this app's observable pull status."""
    state = current_app.extensions["pull_state"]
    with state["lock"]:
        status = dict(state["status"])
        if status["summary"] is not None:
            status["summary"] = dict(status["summary"])
        return status


def update_pull_status(**changes):
    """Update this app's pull status while holding its lock."""
    state = current_app.extensions["pull_state"]
    with state["lock"]:
        state["status"].update(changes)


def calculate_percentage(part_count, total_count):
    """Return a percentage rounded to two places or None for no rows."""

    if total_count == 0:
        return None

    return round(100 * part_count / total_count, 2)


def rounded_average(column):
    """Create a PostgreSQL average expression rounded to two places."""

    return func.round(cast(func.avg(column), Numeric), 2)


def question_2(session: Session, limit=MAX_QUERY_LIMIT):
    """Find the international percentage among classified applicants."""

    classified_statement = select(count(Applicant.p_id)).where(
        Applicant.us_or_international.is_not(None)
    ).limit(clamp_query_limit(limit))
    international_statement = select(count(Applicant.p_id)).where(
        Applicant.us_or_international == "International"
    ).limit(clamp_query_limit(limit))

    classified_count = session.scalar(classified_statement) or 0
    international_count = session.scalar(international_statement) or 0
    return calculate_percentage(international_count, classified_count)


def question_3(session: Session, limit=MAX_QUERY_LIMIT):
    """Find the average of each available GPA and GRE measurement."""

    statement = select(
        rounded_average(Applicant.gpa),
        rounded_average(Applicant.gre),
        rounded_average(Applicant.gre_v),
        rounded_average(Applicant.gre_aw),
    ).limit(clamp_query_limit(limit))
    average_gpa, average_gre, average_gre_v, average_gre_aw = (
        session.execute(statement).one()
    )

    return {
        "gpa": average_gpa,
        "gre": average_gre,
        "gre_v": average_gre_v,
        "gre_aw": average_gre_aw,
    }


def question_6(session: Session, limit=MAX_QUERY_LIMIT):
    """Find the average GPA of accepted Fall 2026 applicants."""

    statement = select(rounded_average(Applicant.gpa)).where(
        and_(
            Applicant.term == "Fall 2026",
            Applicant.status == "Accepted",
            Applicant.gpa.is_not(None),
        )
    ).limit(clamp_query_limit(limit))
    return session.scalar(statement)


def question_7(session: Session, limit=MAX_QUERY_LIMIT) -> int:
    """Count Johns Hopkins Computer Science master's applicants."""

    statement = select(count(Applicant.p_id)).where(
        and_(
            func.lower(Applicant.llm_generated_university)
            == "johns hopkins university",
            func.lower(Applicant.llm_generated_program)
            == "computer science",
            Applicant.degree.ilike("Master%"),
        )
    ).limit(clamp_query_limit(limit))
    return session.scalar(statement) or 0


def question_11(session: Session, limit=MAX_QUERY_LIMIT):
    """Find the average GPA of accepted Johns Hopkins master's applicants."""

    statement = select(rounded_average(Applicant.gpa)).where(
        and_(
            Applicant.status == "Accepted",
            func.lower(Applicant.llm_generated_university)
            == "johns hopkins university",
            Applicant.degree.ilike("Master%"),
            Applicant.gpa.is_not(None),
        )
    ).limit(clamp_query_limit(limit))
    return session.scalar(statement)


def build_analysis_results(session: Session, limit=MAX_QUERY_LIMIT):
    """Run every analysis and organize the answers for the HTML template."""

    # Reuse the questions that already exist in orm_queries.py.
    limit = clamp_query_limit(limit)
    orm_results = collect_orm_results(session, limit=limit)

    # Run only the missing questions defined in this Flask module.
    international_percentage = question_2(session, limit=limit)
    averages = question_3(session, limit=limit)
    accepted_average_gpa = question_6(session, limit=limit)
    johns_hopkins_count = question_7(session, limit=limit)
    johns_hopkins_average_gpa = question_11(session, limit=limit)

    return [
        {
            "number": 1,
            "question": "How many entries are from applicants who applied for Fall 2026?",
            "answers": [
                {"label": "Fall 2026 entries", "value": f"{orm_results['fall_2026_count']:,}"}
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
                    "value": format_decimal(orm_results["american_average_gpa"]),
                }
            ],
        },
        {
            "number": 5,
            "question": "What percentage of Fall 2025 entries are acceptances?",
            "answers": [
                {
                    "label": "Acceptance percentage",
                    "value": format_decimal(orm_results["fall_2025_acceptance_percentage"], "%"),
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
                {"label": "Raw-text matches", "value": f"{orm_results['raw_text_count']:,}"}
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
                    "value": f"{orm_results['llm_standardized_count']:,}",
                },
                {
                    "label": "LLM minus raw-text",
                    "value": f"{orm_results['count_difference']:,}",
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
                    "value": format_decimal(orm_results["nyu_international_percentage"], "%"),
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


def query_analysis(session_factory, limit=MAX_QUERY_LIMIT):
    """Return the dictionary consumed by the analysis template.

    ``analysis_results`` contains eleven dictionaries with ``number``,
    ``question``, ``answers`` and optional ``note`` keys. Each answer contains
    ``label`` and a formatted ``value``. The ORM retains every Module-3 field.
    """
    with session_factory() as session:
        return {"analysis_results": build_analysis_results(session, limit=limit)}


def pull_data():
    """POST /pull-data: return JSON after commit (200), busy (409), or error (500).

    Work runs in the request thread. Other request threads can observe status
    and receive a busy response while scraping/loading is in progress.
    """
    state = current_app.extensions["pull_state"]
    with state["lock"]:
        if state["status"]["state"] == "running":
            return jsonify(busy=True), 409
        state["status"].update(
            state="running", title="Retrieving new GradCafe data",
            message="Collecting and saving applicant records.",
            started_at=datetime.now().astimezone().isoformat(),
            finished_at=None, summary=None,
        )
    try:
        summary = run_pull_pipeline(**current_app.extensions["etl"])
    # Injected ETL callbacks can raise any exception; always release the busy state.
    except Exception:  # pylint: disable=broad-exception-caught
        current_app.logger.exception("Unable to pull new GradCafe data")
        update_pull_status(
            state="error", title="The data pull did not finish",
            message="No changes were committed. Check the server log for details.",
            finished_at=datetime.now().astimezone().isoformat(), summary=None,
        )
        return jsonify(ok=False, error="Data pull failed"), 500
    update_pull_status(
        state="success", title="GradCafe data pull completed",
        message=(f"Processed {summary['processed_rows']} records. Added "
                 f"{summary['inserted_rows']} new records and refreshed "
                 f"{summary['updated_rows']} existing records. Select Update "
                 "Analysis to display the newly committed data."),
        finished_at=datetime.now().astimezone().isoformat(), summary=summary,
    )
    return jsonify(ok=True), 200


def pull_status_endpoint():
    """GET /pull-status: return JSON describing the current or last pull."""
    return jsonify(get_pull_status())


def index():
    """GET /analysis or /: render current committed analysis, or HTTP 500."""
    try:
        clamp_query_limit(request.args.get("limit", MAX_QUERY_LIMIT))
    except ValueError:
        return jsonify(error="limit must be an integer"), 400
    try:
        context = current_app.extensions["analysis_query"]()
    except SQLAlchemyError:
        current_app.logger.exception("Unable to load applicant analysis")
        return render_template(
            "index.html", analysis_results=[], generated_at=None,
            pull_status=get_pull_status(),
            error="The analysis could not be loaded. Check PostgreSQL and DATABASE_URL.",
        ), 500
    return render_template(
        "index.html", **context, generated_at=datetime.now().astimezone(),
        pull_status=get_pull_status(), error=None,
    )


def update_analysis():
    """POST /update-analysis: refresh HTML, or return {busy: true} with 409."""
    state = current_app.extensions["pull_state"]
    with state["lock"]:
        if state["status"]["state"] == "running":
            return jsonify(busy=True), 409
    return index()


def health():
    """Expose web-process health without performing a database query."""
    return jsonify(status="ok")


def enqueue_job():
    """Publish a minimal job so the scaffold can demonstrate broker delivery."""
    job = request.get_json(silent=True)
    try:
        publish_job(job)
    except (ValueError, TypeError):
        return jsonify(error="task must be 'noop' or 'scrape'"), 400
    except (pika.exceptions.AMQPError, OSError):
        return jsonify(error="Message broker unavailable"), 503
    return jsonify(queued=True), 202


def create_app(config=None, *, scraper=None, cleaner=None, loader=None, query=None):
    """Create an independent Flask app with optional ETL and query functions.

    ``config`` may override ``DATABASE_URL`` and Flask settings. ``query`` takes
    no arguments and returns the template dictionary from :func:`query_analysis`.
    Inject all four functions to run web tests without PostgreSQL or the network.
    """
    app = Flask(__name__)
    app.config.from_mapping(config or {})
    app.extensions["pull_state"] = {
        "lock": Lock(),
        "status": {
            "state": "idle", "title": "No data pull is running",
            "message": "The analysis is using the current PostgreSQL data.",
            "started_at": None, "finished_at": None, "summary": None,
        },
    }
    if query is None:
        factory = create_session_factory(app.config.get("DATABASE_URL"))
        # SQLAlchemy creates sessionmaker.kw at runtime; Pylint cannot infer it.
        app.extensions["database_engine"] = factory.kw["bind"]  # pylint: disable=no-member

        def default_query():
            """Query the database configured for this app."""
            return query_analysis(
                factory, limit=clamp_query_limit(request.args.get("limit", MAX_QUERY_LIMIT))
            )

        query = default_query
    if loader is None:
        def default_loader(records):
            """Load records using this app's current database configuration."""
            return load_cleaned_records(
                records, database_url=app.config.get("DATABASE_URL")
            )

        loader = default_loader
    app.extensions["analysis_query"] = query
    app.extensions["etl"] = {"scraper": scraper, "cleaner": cleaner, "loader": loader}
    app.add_url_rule("/", view_func=index)
    app.add_url_rule("/health", view_func=health)
    app.add_url_rule("/jobs", view_func=enqueue_job, methods=["POST"])
    app.add_url_rule("/analysis", view_func=index)
    app.add_url_rule("/pull-data", view_func=pull_data, methods=["POST"])
    app.add_url_rule("/pull-status", view_func=pull_status_endpoint)
    app.add_url_rule("/update-analysis", view_func=update_analysis, methods=["POST"])
    return app


if __name__ == "__main__":
    create_app().run()
