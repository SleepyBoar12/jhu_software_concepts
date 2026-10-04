### The SQL Query Analysis; must answer questions with SQL queries
### Output an analysis that is expressed in SQL
"""
SQL Queries to answer the following questions:
All count in whole number
ALL percentages, GPA, GRE quant, GRE verbal, and GRE analytical scores in 2 DECIMAL PLACES
1. How many entries in your database are from applicants who applied for Fall 2026?
2. Among entries that provided a nationality classification, what percentage are international students?
3. What are the average GPA, GRE Quantitative, GRE Verbal, and GRE Analytical Writing scores of applicants who provided each metric?
4. What is the Average GPA of American applicants who applied for Fall 2026?
5. WHat percentage of Fall 2025 entries are acceptances?
6. What is the average GPA of accepted applicants who applied in Fall 2026?
7. How many entries are from applicants who applied to Johns Hopkins University for a master's degree in Computer Science?
8. How many Fall 2026 entries are acceptances from applicants applying for a PhD in Computer Science at Georgetown University, MIT, Stanford, and Carnegie Mellon?
9. Identify universities and programs LLM generated terms. Report Question 8 and Question 9 count for term, degree, and admissions status. Report the difference between them
10. What percentage of students getting accepted at NYU master's program are international?
11. What is the average GPA of students accepted for Johns Hopkins master's program?
"""

import os
from decimal import Decimal
from pathlib import Path

import psycopg
from dotenv import load_dotenv


### Load the same private database connection settings used by load_data.py.
module_3_directory = Path(__file__).resolve().parent
env_file = module_3_directory / ".env"

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


### Raw text may use "MIT" while the LLM field uses the full university name.
raw_universities_for_question_8 = [
    "Georgetown University",
    "MIT",
    "Massachusetts Institute of Technology",
    "Stanford University",
    "Carnegie Mellon University",
]

llm_universities_for_question_9 = [
    "georgetown university",
    "massachusetts institute of technology",
    "stanford university",
    "carnegie mellon university",
]


### 1. Count applicants who applied for the Fall 2026 term.
question_1_sql = """
SELECT COUNT(*) AS fall_2026_entries
FROM applicants
WHERE term = %s;
"""


### 2. Calculate the international percentage only among classified applicants.
question_2_sql = """
SELECT ROUND(
    100.0 * COUNT(*) FILTER (
        WHERE us_or_international = 'International'
    ) / NULLIF(COUNT(*), 0),
    2
) AS international_percentage
FROM applicants
WHERE us_or_international IS NOT NULL;
"""


### 3. AVG automatically ignores applicants whose metric is SQL NULL.
question_3_sql = """
SELECT
    ROUND(AVG(gpa)::NUMERIC, 2) AS average_gpa,
    ROUND(AVG(gre)::NUMERIC, 2) AS average_gre,
    ROUND(AVG(gre_v)::NUMERIC, 2) AS average_gre_verbal,
    ROUND(AVG(gre_aw)::NUMERIC, 2) AS average_gre_writing
FROM applicants;
"""


### 4. Find the average GPA of American Fall 2026 applicants.
question_4_sql = """
SELECT ROUND(AVG(gpa)::NUMERIC, 2) AS average_american_gpa
FROM applicants
WHERE term = %s
  AND us_or_international = %s
  AND gpa IS NOT NULL;
"""


### 5. Calculate the acceptance percentage for Fall 2025 applicants.
question_5_sql = """
SELECT ROUND(
    100.0 * COUNT(*) FILTER (
        WHERE status = 'Accepted'
    ) / NULLIF(COUNT(*), 0),
    2
) AS fall_2025_acceptance_percentage
FROM applicants
WHERE term = %s;
"""


### 6. Find the average GPA of accepted Fall 2026 applicants.
question_6_sql = """
SELECT ROUND(AVG(gpa)::NUMERIC, 2) AS accepted_average_gpa
FROM applicants
WHERE term = %s
  AND status = %s
  AND gpa IS NOT NULL;
"""


### 7. Use the standardized LLM fields for an exact program/university match.
question_7_sql = """
SELECT COUNT(*) AS johns_hopkins_cs_masters_entries
FROM applicants
WHERE LOWER(llm_generated_university) = LOWER(%s)
  AND LOWER(llm_generated_program) = LOWER(%s)
  AND degree ILIKE %s;
"""


### 8 and 9. Compare raw text matching with the standardized LLM fields.
### The difference shows how much standardization changes the result count.
questions_8_and_9_sql = """
WITH raw_text_matches AS (
    SELECT COUNT(*) AS match_count
    FROM applicants AS applicant
    WHERE applicant.term = %s
      AND applicant.degree = %s
      AND applicant.status = %s
      AND POSITION(
          'computer science' IN LOWER(applicant.program)
      ) > 0
      AND EXISTS (
          SELECT 1
          FROM UNNEST(%s::TEXT[]) AS selected(university)
          WHERE POSITION(
              LOWER(selected.university) IN LOWER(applicant.program)
          ) > 0
      )
),
llm_matches AS (
    SELECT COUNT(*) AS match_count
    FROM applicants
    WHERE term = %s
      AND degree = %s
      AND status = %s
      AND LOWER(llm_generated_program) = 'computer science'
      AND LOWER(llm_generated_university) = ANY(%s::TEXT[])
)
SELECT
    raw_text_matches.match_count AS raw_text_count,
    llm_matches.match_count AS llm_standardized_count,
    llm_matches.match_count
        - raw_text_matches.match_count AS count_difference
FROM raw_text_matches
CROSS JOIN llm_matches;
"""


### 10. Find the international percentage among accepted NYU master's applicants.
question_10_sql = """
SELECT ROUND(
    100.0 * COUNT(*) FILTER (
        WHERE us_or_international = 'International'
    ) / NULLIF(COUNT(*), 0),
    2
) AS nyu_international_percentage
FROM applicants
WHERE status = %s
  AND LOWER(llm_generated_university) = LOWER(%s)
  AND degree ILIKE %s;
"""


### 11. Find the GPA average among accepted Johns Hopkins master's applicants.
question_11_sql = """
SELECT ROUND(AVG(gpa)::NUMERIC, 2) AS johns_hopkins_average_gpa
FROM applicants
WHERE status = %s
  AND LOWER(llm_generated_university) = LOWER(%s)
  AND degree ILIKE %s
  AND gpa IS NOT NULL;
"""


def format_value(value):
    """Display missing values clearly and decimals with two places."""
    if value is None:
        return "N/A"

    if isinstance(value, Decimal):
        return f"{value:.2f}"

    return str(value)


applicant_fields = (
    "p_id",
    "program",
    "comments",
    "date_added",
    "url",
    "status",
    "term",
    "us_or_international",
    "gpa",
    "gre",
    "gre_v",
    "gre_aw",
    "degree",
    "llm_generated_program",
    "llm_generated_university",
)


def get_applicant_by_url(cursor, applicant_url):
    """Select an applicant using a bound URL parameter.

    :param cursor: Open psycopg cursor for the configured applicants table.
    :param applicant_url: Exact source URL identifying the applicant.
    :returns: Applicant dictionary, or ``None`` when the URL has no match.
    """
    selected_fields = ", ".join(applicant_fields)
    cursor.execute(
        f"SELECT {selected_fields} FROM applicants WHERE url = %s",
        (applicant_url,),
    )
    row = cursor.fetchone()

    if row is None:
        return None

    return dict(zip(applicant_fields, row, strict=True))


def run_query(cursor, question, sql_expression, parameters=()):
    """Execute one SQL expression and print its column names and results."""
    cursor.execute(sql_expression, parameters)
    column_names = [column.name for column in cursor.description]
    rows = cursor.fetchall()

    print(f"\n{question}")
    print(" | ".join(column_names))
    print("-" * 72)

    if not rows:
        print("No matching records")
        return

    for row in rows:
        print(" | ".join(format_value(value) for value in row))


def main():
    """Connect to PostgreSQL and run each assignment question in order."""
    with psycopg.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ["PGPORT"]),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    ) as connection:
        with connection.cursor() as cursor:
            run_query(
                cursor,
                "1. Fall 2026 applicant count",
                question_1_sql,
                ("Fall 2026",),
            )
            run_query(
                cursor,
                "2. Percentage of classified applicants who are international",
                question_2_sql,
            )
            run_query(
                cursor,
                "3. Average reported GPA and GRE scores",
                question_3_sql,
            )
            run_query(
                cursor,
                "4. Average GPA of American Fall 2026 applicants",
                question_4_sql,
                ("Fall 2026", "American"),
            )
            run_query(
                cursor,
                "5. Fall 2025 acceptance percentage",
                question_5_sql,
                ("Fall 2025",),
            )
            run_query(
                cursor,
                "6. Average GPA of accepted Fall 2026 applicants",
                question_6_sql,
                ("Fall 2026", "Accepted"),
            )
            run_query(
                cursor,
                "7. Johns Hopkins Computer Science master's count",
                question_7_sql,
                (
                    "Johns Hopkins University",
                    "Computer Science",
                    "Master%",
                ),
            )

            run_query(
                cursor,
                "8–9. Raw-text count versus LLM-standardized count",
                questions_8_and_9_sql,
                (
                    "Fall 2026",
                    "PhD",
                    "Accepted",
                    raw_universities_for_question_8,
                    "Fall 2026",
                    "PhD",
                    "Accepted",
                    llm_universities_for_question_9,
                ),
            )

            run_query(
                cursor,
                "10. International percentage among accepted "
                "NYU master's applicants",
                question_10_sql,
                (
                    "Accepted",
                    "New York University",
                    "Master%",
                ),
            )
            run_query(
                cursor,
                "11. Average GPA of accepted Johns Hopkins "
                "master's applicants",
                question_11_sql,
                (
                    "Accepted",
                    "Johns Hopkins University",
                    "Master%",
                ),
            )


if __name__ == "__main__":
    main()
