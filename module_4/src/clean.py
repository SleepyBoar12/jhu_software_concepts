from bs4 import BeautifulSoup as bs
from pathlib import Path
import json
import re

### I used GPT to help create after specifying parts and bit of the requirement
"""
Convert the GradCafe HTML pages saved by scrape.py into structured JSON records.

Each applicant is displayed using more than one table row:
    1. A main row containing the university, program, degree, date, decision, and URL.
    2. A details row containing badges such as the term, student type, GRE, and GPA.
    3. An optional row containing the applicant's comments.

The parser groups those rows together before creating one dictionary per applicant.
"""


### Build paths relative to module_4 so the script works from any directory.
### ALL PARAMETERS ARE WRITTEN HERE
folder_dir = Path(__file__).resolve().parent.parent
# Write "test" or "cleaned" in "location" depending on where in the module 
# you want the output to go
location_from = "collected"
location_to = "cleaned"
html_path = folder_dir /location_from
output_path = folder_dir /location_to
json_file = output_path / "applicant_data.json"

# helper funtion made by RE to "pick out" the GRE scores
def _get_badge_value(badges, prefix, pattern=None):
    """Return the value portion of a badge such as 'GPA 3.57'."""
    for badge in badges:
        # GRE, GRE V, and GRE AW begin similarly. A pattern lets the caller make
        # an exact distinction when checking the general GRE score.
        if pattern is not None:
            if re.fullmatch(pattern, badge):
                return badge.removeprefix(prefix)
        elif badge.startswith(prefix):
            return badge.removeprefix(prefix)

    # For the NA, returning None
    return None

# helper function use BeautifulSoup to get HTML
def _parse_html_file(html_file):
    """Extract all applicant records from one saved GradCafe HTML file."""
    html = html_file.read_text(encoding="utf-8")
    soup = bs(html, "html.parser")

    # The admissions records are inside the table body. Returning an empty list
    # keeps one malformed or incomplete page from crashing the whole collection.
    table_body = soup.select_one("main table tbody")
    if table_body is None:
        print(f"Warning: no results table found in {html_file.name}")
        return []

    # recursive=False selects only rows that directly belong to this table body.
    rows = table_body.find_all("tr", recursive=False)
    applicants = []
    index = 0

    while index < len(rows):
        main_row = rows[index]

        # A /result/ link uniquely identifies the first row of an applicant entry.
        # Rows without this link are detail, comment, advertisement, or empty rows.
        result_link = main_row.select_one('a[href^="/result/"]')
        if result_link is None:
            index += 1
            continue

        cells = main_row.find_all("td", recursive=False)
        if len(cells) < 5:
            print(f"Warning: incomplete applicant row in {html_file.name}")
            index += 1
            continue

        # The second cell contains two spans: program name followed by degree type.
        program_parts = cells[1].find_all("span")
        program_name = (
            program_parts[0].get_text(" ", strip=True)
            if program_parts
            else None
        )
        degree = (
            program_parts[-1].get_text(" ", strip=True)
            if len(program_parts) > 1
            else None
        )

        university = cells[0].get_text(" ", strip=True)
        date_added = cells[2].get_text(" ", strip=True)

        # Split strings such as "Accepted on Sep 09" into a status and date.
        # Doable because it is a standardized format
        decision_text = cells[3].get_text(" ", strip=True)
        applicant_status, separator, decision_date = decision_text.partition(" on ")
        if not separator:
            decision_date = None

        # The HTML contains /result/1020480. Extract the ID and use the known
        # GradCafe result route to create a complete applicant URL.
        result_id = result_link["href"].rstrip("/").rsplit("/", 1)[-1]
        applicant_url = f"https://www.thegradcafe.com/result/{result_id}"

        # Everything after the main row belongs to this applicant until another
        # row with a /result/ link begins the next applicant entry.
        badges = []
        comments = []
        index += 1

        while index < len(rows):
            extra_row = rows[index]

            if extra_row.select_one('a[href^="/result/"]') is not None:
                break

            comment = extra_row.find("p")
            if comment is not None:
                comment_text = comment.get_text(" ", strip=True)
                if comment_text:
                    comments.append(comment_text)
            else:
                # stripped_strings returns the visible text of the detail badges.
                badges.extend(extra_row.stripped_strings)

            index += 1

        # Search the badges for a term formatted like "Fall 2026" or "Spring 2027".
        program_start = next((badge for badge in badges
                if re.fullmatch(r"(?:Fall|Spring) \d{4}", badge)
            ),
            None,
        )

        student_type = next((badge for badge in badges
                if badge in {"International", "American", "Other"}
            ),
            None,
        )

        #LLM_hosting not working so I changed the field in "program_name" to just "program"
        applicant = {
            "program": f"{program_name}, {university}",
            "comments": " ".join(comments) or None,
            "date_added": date_added,
            "url": applicant_url,
            "applicant_status": applicant_status,
            # Only fill the date column that agrees with the decision status.
            "acceptance_date": (
                decision_date if applicant_status == "Accepted" else None
            ),
            "rejection_date": (
                decision_date if applicant_status == "Rejected" else None
            ),
            "program_start": program_start,
            "student_type": student_type,
            # The pattern prevents "GRE V" and "GRE AW" from being mistaken for
            # the general quantitative GRE badge.
            "gre_score": _get_badge_value(
                badges,
                "GRE ",
                r"GRE \d+(?:\.\d+)?",
            ),
            "gre_v_score": _get_badge_value(badges, "GRE V "),
            "degree": degree,
            "gpa": _get_badge_value(badges, "GPA "),
            "gre_aw": _get_badge_value(badges, "GRE AW "),
        }

        applicants.append(applicant)

    return applicants

### The main function that brings everything together
def clean_data(input_directory=html_path):
    """Parse every data_*.html file from one directory."""
    input_directory = Path(input_directory)

    if not input_directory.exists():
        raise FileNotFoundError(
            f"Collected HTML folder does not exist: {input_directory}"
        )

    # Sort by numbers in the filename so data_2 comes before data_10.
    html_files = sorted(
        input_directory.glob("data_*.html"),
        key=lambda path: int(path.stem.rsplit("_", 1)[-1]),
    )

    if not html_files:
        raise FileNotFoundError(
            f"No data_*.html files found in: {input_directory}"
        )

    all_applicants = []
    for html_file in html_files:
        all_applicants.extend(_parse_html_file(html_file))

    return all_applicants

### Saving the data into the "cleaned" folder
def save_data(data, output_file=json_file):
    """Save applicant dictionaries as readable UTF-8 JSON, in "cleaned" folder."""
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

### Getting a dictionary out of the JSON file
def load_data(input_file=json_file):
    """Load and return applicant dictionaries from the generated JSON file."""
    return json.loads(input_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    cleaned_applicants = clean_data()
    save_data(cleaned_applicants)
    print(f"Saved {len(cleaned_applicants)} records to {json_file}")
