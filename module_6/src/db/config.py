"""Shared PostgreSQL settings, independent of Flask and analytics."""

import os
from pathlib import Path
from urllib.parse import quote, urlencode

from dotenv import load_dotenv
from sqlalchemy import URL, make_url


def get_database_url(database_url=None):
    """Return a PostgreSQL URL; an explicit value overrides the environment.

    ``src/.env`` is optional. ``DATABASE_URL`` is preferred. Otherwise,
    ``DB_HOST`` overrides ``PGHOST``; the remaining Module-3 ``PG*`` settings
    remain supported for existing installations.
    No credentials are included in configuration errors.
    """
    if database_url is None:
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        database_url = os.getenv("DATABASE_URL")
    if not database_url:
        host = os.getenv("DB_HOST") or os.getenv("PGHOST")
        required = ("PGDATABASE", "PGUSER")
        if not host or not all(os.getenv(name) for name in required):
            raise RuntimeError("Set DATABASE_URL or DB_HOST/PGHOST, PGDATABASE, and PGUSER")
        database_url = URL.create(
            "postgresql",
            username=os.environ["PGUSER"],
            password=os.getenv("PGPASSWORD"),
            host=host,
            port=int(os.getenv("PGPORT", "5432")),
            database=os.environ["PGDATABASE"],
        )
    url = make_url(database_url)
    if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
        raise ValueError("DATABASE_URL must use PostgreSQL")
    return url.set(drivername="postgresql")


def connection_string(database_url=None):
    """Return the psycopg connection URI for the configured database."""
    url = get_database_url(database_url)
    uri = url.set(query={}).render_as_string(hide_password=False)
    # libpq decodes percent escapes, but treats '+' literally in query values.
    query = urlencode(url.query, doseq=True, quote_via=quote)
    return uri + ("?" + query if query else "")
