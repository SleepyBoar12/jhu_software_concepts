"""Validate cleaned GradCafe records and upsert PostgreSQL rows by unique URL."""

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg
from psycopg import sql

from .database import connection_string
from .query_limits import MAX_QUERY_LIMIT


### Build paths relative to module_4 so the program works from any directory.
src_directory = Path(__file__).resolve().parent
module_4_directory = src_directory.parent
json_file = (
    module_4_directory
    / "cleaned"
    / "llm_extended_applicant_data.json"
)

# Insert records in batches instead of holding every database operation at once.
BATCH_SIZE = 1_000


def required_text(record, field, line_number):
    """Return a required text value or stop when it is missing."""
    value = record.get(field)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Line {line_number} has no valid {field!r} value"
        )

    return value.strip()


def optional_text(record, field):
    """Convert missing or blank optional text to Python None/SQL NULL."""
    value = record.get(field)

    if value is None:
        return None

    value = str(value).strip()
    return value or None


def optional_decimal(record, field, line_number):
    """Convert an optional numeric string into a PostgreSQL-safe number."""
    value = record.get(field)

    if value is None or not str(value).strip():
        return None

    try:
        number = Decimal(str(value).strip())
    except InvalidOperation as error:
        raise ValueError(
            f"Line {line_number} has invalid {field!r}: {value!r}"
        ) from error

    if not number.is_finite():
        raise ValueError(
            f"Line {line_number} has invalid {field!r}: {value!r}"
        )

    return number


def prepare_record(record, line_number):
    """Validate one JSON object and match its values to the SQL columns."""
    if not isinstance(record, dict):
        raise ValueError(
            f"Line {line_number} must contain one JSON object"
        )

    date_text = required_text(record, "date_added", line_number)

    try:
        date_added = datetime.strptime(date_text, "%b %d, %Y").date()
    except ValueError as error:
        raise ValueError(
            f"Line {line_number} has invalid date_added: {date_text!r}"
        ) from error

    return {
        "program": required_text(record, "program", line_number),
        "comments": optional_text(record, "comments"),
        "date_added": date_added,
        "url": required_text(record, "url", line_number),
        "status": required_text(
            record,
            "applicant_status",
            line_number,
        ),
        "term": optional_text(record, "program_start"),
        "us_or_international": optional_text(record, "student_type"),
        "gre": optional_decimal(record, "gre_score", line_number),
        "gre_v": optional_decimal(
            record,
            "gre_v_score",
            line_number,
        ),
        "degree": optional_text(record, "degree"),
        "gpa": optional_decimal(record, "gpa", line_number),
        "gre_aw": optional_decimal(record, "gre_aw", line_number),
        # The JSON names use hyphens, but SQL column names use underscores.
        "llm_generated_program": optional_text(
            record,
            "llm-generated-program",
        ),
        "llm_generated_university": optional_text(
            record,
            "llm-generated-university",
        ),
    }


def read_records(input_file):
    """Read and validate a JSON Lines file, skipping blank lines.

    :param input_file: :class:`pathlib.Path` containing one JSON object per line.
    :yields: Prepared records accepted by :func:`load_records`.
    :raises FileNotFoundError: The input file does not exist.
    :raises ValueError: A line contains invalid JSON or invalid applicant data.
    """
    if not input_file.is_file():
        raise FileNotFoundError(f"Applicant data not found: {input_file}")

    with input_file.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            # Ignore accidental blank lines between JSON records.
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Line {line_number} is not valid JSON"
                ) from error

            yield prepare_record(record, line_number)


def make_batches(records, size):
    """Group applicant records into smaller lists for database insertion."""
    batch = []

    for record in records:
        batch.append(record)

        if len(batch) == size:
            yield batch
            batch = []

    # Yield the final partial batch when fewer than size records remain.
    if batch:
        yield batch


### Create the table when it does not exist. The URL constraint prevents duplicates.
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS applicants (
    p_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    program TEXT NOT NULL,
    comments TEXT,
    date_added DATE NOT NULL,
    url TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    term TEXT,
    us_or_international TEXT,
    gpa DOUBLE PRECISION,
    gre DOUBLE PRECISION,
    gre_v DOUBLE PRECISION,
    gre_aw DOUBLE PRECISION,
    degree TEXT,
    llm_generated_program TEXT,
    llm_generated_university TEXT
);
"""


### Insert new URLs and update an existing URL only when its data has changed.
UPSERT_SQL = """
INSERT INTO applicants (
    program,
    comments,
    date_added,
    url,
    status,
    term,
    us_or_international,
    gpa,
    gre,
    gre_v,
    gre_aw,
    degree,
    llm_generated_program,
    llm_generated_university
)
VALUES (
    %(program)s,
    %(comments)s,
    %(date_added)s,
    %(url)s,
    %(status)s,
    %(term)s,
    %(us_or_international)s,
    %(gpa)s,
    %(gre)s,
    %(gre_v)s,
    %(gre_aw)s,
    %(degree)s,
    %(llm_generated_program)s,
    %(llm_generated_university)s
)
ON CONFLICT (url) DO UPDATE SET
    program = EXCLUDED.program,
    comments = EXCLUDED.comments,
    date_added = EXCLUDED.date_added,
    status = EXCLUDED.status,
    term = EXCLUDED.term,
    us_or_international = EXCLUDED.us_or_international,
    gpa = EXCLUDED.gpa,
    gre = EXCLUDED.gre,
    gre_v = EXCLUDED.gre_v,
    gre_aw = EXCLUDED.gre_aw,
    degree = EXCLUDED.degree,
    llm_generated_program = COALESCE(
        EXCLUDED.llm_generated_program,
        applicants.llm_generated_program
    ),
    llm_generated_university = COALESCE(
        EXCLUDED.llm_generated_university,
        applicants.llm_generated_university
    )
WHERE ROW(
    applicants.program,
    applicants.comments,
    applicants.date_added,
    applicants.status,
    applicants.term,
    applicants.us_or_international,
    applicants.gpa,
    applicants.gre,
    applicants.gre_v,
    applicants.gre_aw,
    applicants.degree,
    applicants.llm_generated_program,
    applicants.llm_generated_university
) IS DISTINCT FROM ROW(
    EXCLUDED.program,
    EXCLUDED.comments,
    EXCLUDED.date_added,
    EXCLUDED.status,
    EXCLUDED.term,
    EXCLUDED.us_or_international,
    EXCLUDED.gpa,
    EXCLUDED.gre,
    EXCLUDED.gre_v,
    EXCLUDED.gre_aw,
    EXCLUDED.degree,
    COALESCE(
        EXCLUDED.llm_generated_program,
        applicants.llm_generated_program
    ),
    COALESCE(
        EXCLUDED.llm_generated_university,
        applicants.llm_generated_university
    )
);
"""


def load_records(records, database_url=None):
    """Upsert prepared records and return a summary of database changes."""
    processed_rows = 0
    changed_rows = 0
    count_stmt = sql.SQL("SELECT COUNT(*) FROM {table} LIMIT %s").format(
        table=sql.Identifier("applicants")
    )
    count_params = (MAX_QUERY_LIMIT,)
    upsert_stmt = sql.SQL(UPSERT_SQL)

    # The connection commits on success and rolls everything back on an error.
    with psycopg.connect(connection_string(database_url)) as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TABLE_SQL)
            cursor.execute(count_stmt, count_params)
            total_rows_before = cursor.fetchone()[0]

            for batch in make_batches(records, BATCH_SIZE):
                cursor.executemany(upsert_stmt, batch)
                processed_rows += len(batch)

                # rowcount includes new rows and existing rows that changed.
                if cursor.rowcount > 0:
                    changed_rows += cursor.rowcount

            cursor.execute(count_stmt, count_params)
            total_rows_after = cursor.fetchone()[0]

    inserted_rows = max(total_rows_after - total_rows_before, 0)
    updated_rows = max(changed_rows - inserted_rows, 0)
    return {
        "processed_rows": processed_rows,
        "inserted_rows": inserted_rows,
        "updated_rows": updated_rows,
        "total_rows": total_rows_after,
    }


def load_cleaned_records(records, database_url=None):
    """Validate cleaned dictionaries and commit PostgreSQL upserts.

    :param records: Iterable of dictionaries using the cleaner's field names.
    :returns: Dictionary with ``processed_rows``, ``inserted_rows``,
        ``updated_rows``, and ``total_rows`` counts.
    :raises ValueError: Required fields, dates, or numeric scores are invalid.

    The loader creates the table when needed. Repeated URLs update existing
    applicants instead of creating duplicate rows; database errors roll back
    the transaction and propagate to the caller.
    """

    prepared_records = (
        prepare_record(record, record_number)
        for record_number, record in enumerate(records, start=1)
    )
    return load_records(prepared_records, database_url=database_url)


def main():
    """Load the saved LLM-extended JSON file into PostgreSQL."""

    summary = load_records(read_records(json_file))

    print(f"Processed {summary['processed_rows']} JSON records")
    print(f"Inserted {summary['inserted_rows']} database records")
    print(f"Updated {summary['updated_rows']} database records")
    print(f"The applicants table contains {summary['total_rows']} records")


if __name__ == "__main__":
    main()
