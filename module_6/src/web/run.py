"""Initialize the schema and start the Flask service on port 8080."""

from ..db.load_data import load_cleaned_records
from .app.flask_app import create_app


def main():
    """Start a reachable web service without inserting placeholder data."""
    load_cleaned_records([])
    create_app().run(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
