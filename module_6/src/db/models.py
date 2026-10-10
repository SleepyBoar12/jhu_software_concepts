"""Define the applicant ORM model and manage PostgreSQL sessions."""

from contextlib import contextmanager
from datetime import date

from sqlalchemy import (
    Date,
    Double,
    Identity,
    Integer,
    Text,
    create_engine,
    select,
)

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)
from sqlalchemy.sql.functions import count

from .config import get_database_url

MAX_QUERY_LIMIT = 50


def create_session_factory(database_url=None):
    """Create sessions for a PostgreSQL URL without opening a connection yet."""
    engine = create_engine(
        get_database_url(database_url).set(drivername="postgresql+psycopg"),
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_local(database_url=None):
    """Open one CLI session and dispose its engine when finished."""
    factory = create_session_factory(database_url)
    try:
        with factory() as session:
            yield session
    finally:
        # SQLAlchemy creates sessionmaker.kw at runtime; Pylint cannot infer it.
        factory.kw["bind"].dispose()  # pylint: disable=no-member


# SQLAlchemy models define their interface through mapped columns.
class Base(DeclarativeBase):  # pylint: disable=too-few-public-methods
    """Provide the base class inherited by SQLAlchemy models."""


class Applicant(Base):  # pylint: disable=too-few-public-methods
    """Represent one row in the PostgreSQL applicants table."""

    __tablename__ = "applicants"

    p_id: Mapped[int] = mapped_column(
        Integer,
        Identity(always=True),
        primary_key=True)

    program: Mapped[str] = mapped_column(Text, nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_added: Mapped[date] = mapped_column(Date, nullable=False)
    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True)

    status: Mapped[str] = mapped_column(Text, nullable=False)
    term: Mapped[str | None] = mapped_column(Text, nullable=True)
    us_or_international: Mapped[str | None] = mapped_column(
        Text,
        nullable=True)

    gpa: Mapped[float | None] = mapped_column(Double, nullable=True)
    gre: Mapped[float | None] = mapped_column(Double, nullable=True)
    gre_v: Mapped[float | None] = mapped_column(Double, nullable=True)
    gre_aw: Mapped[float | None] = mapped_column(Double, nullable=True)
    degree: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_generated_program: Mapped[str | None] = mapped_column(
        Text,
        nullable=True)

    llm_generated_university: Mapped[str | None] = mapped_column(
        Text,
        nullable=True)

    def __repr__(self):
        """Return a readable description for debugging."""

        return (
            f"Applicant(p_id={self.p_id!r}, "
            f"program={self.program!r}, "
            f"status={self.status!r})")

def test_connection():
    """Connect to PostgreSQL and count the applicant records."""

    with session_local() as session:
        statement = select(count()).select_from(Applicant).limit(MAX_QUERY_LIMIT)
        applicant_count = session.scalar(statement)

        print("Successfully connected to PostgreSQL.")
        print(f"Applicant rows: {applicant_count}")


if __name__ == "__main__":
    test_connection()
