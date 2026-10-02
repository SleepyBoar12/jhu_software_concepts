### Create "Applicant" with SQLAlchemy and answer all the SQL questions with model & create a dynamic web application

import os
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import (
    URL,
    Date,
    Double,
    Identity,
    Integer,
    Text,
    create_engine,
    func,
    select)

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker)

### Load database credentials from module_3/.env.
module_directory = Path(__file__).resolve().parent
env_file = module_directory / ".env"

if not env_file.is_file():
    raise FileNotFoundError(f"Environment file not found: {env_file}")

load_dotenv(env_file)

### Build a PostgreSQL connection URL
database_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.environ["PGUSER"],
    password=os.environ["PGPASSWORD"],
    host=os.environ["PGHOST"],
    port=int(os.environ["PGPORT"]),
    database=os.environ["PGDATABASE"])


### Create the reusable SQLAlchemy connection engine.
engine = create_engine(
    database_url,
    pool_pre_ping=True)

### Create database sessions for queries and application requests.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False)

class Base(DeclarativeBase):
    """Provide the base class inherited by SQLAlchemy models."""

class Applicant(Base):
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

    with SessionLocal() as session:
        statement = select(func.count()).select_from(Applicant)
        applicant_count = session.scalar(statement)

        print("Successfully connected to PostgreSQL.")
        print(f"Applicant rows: {applicant_count}")


if __name__ == "__main__":
    test_connection()