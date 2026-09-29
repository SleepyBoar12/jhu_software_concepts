### Take the cleaned, LLM-extended applicant data and load it into PostgreSQL.
### The applicant URL is unique, so rerunning this file will not create duplicates.

import json
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg
from dotenv import load_dotenv


### Build paths relative to this file so the program works from any directory.
module_3_directory = Path(__file__).resolve().parent
env_file = module_3_directory / ".env"
json_file = (
    module_3_directory.parent
    / "module_2"
    / "cleaned"
    / "llm_extended_applicant_data.json"
)

# Insert records in batches instead of holding every database operation at once.
batch_size = 1_000


### Load the private PostgreSQL connection settings from module_3/.env.
if not env_file.is_file():
    raise FileNotFoundError(f"Environment file not found: {env_file}")

load_dotenv(env_file)

required_environment_variables = (
    "PGHOST",
    "PGPORT",
    "PGDATABASE",
    "PGUSER",
    "PGPASSWORD",
)

missing_environment_variables = [
    variable
    for variable in required_environment_variables
    if not os.getenv(variable)
]

if missing_environment_variables:
    raise RuntimeError(
        "Missing environment variables: "
        f"{missing_environment_variables}"
    )


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
    """Read and validate the newline-delimited JSON file one line at a time."""
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
create_table_sql = """
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
upsert_sql = """
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
    llm_generated_program = EXCLUDED.llm_generated_program,
    llm_generated_university = EXCLUDED.llm_generated_university
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
    EXCLUDED.llm_generated_program,
    EXCLUDED.llm_generated_university
);
"""


def main():
    """Connect to PostgreSQL and load every applicant in one transaction."""
    processed_rows = 0
    changed_rows = 0

    # The connection commits on success and rolls everything back on an error.
    with psycopg.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ["PGPORT"]),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(create_table_sql)

            records = read_records(json_file)

            for batch in make_batches(records, batch_size):
                cursor.executemany(upsert_sql, batch)
                processed_rows += len(batch)

                # rowcount includes new rows and existing rows that changed.
                if cursor.rowcount > 0:
                    changed_rows += cursor.rowcount

            cursor.execute("SELECT COUNT(*) FROM applicants")
            total_rows = cursor.fetchone()[0]

    print(f"Processed {processed_rows} JSON records")
    print(f"Inserted or updated {changed_rows} database records")
    print(f"The applicants table contains {total_rows} records")


if __name__ == "__main__":
    main()
