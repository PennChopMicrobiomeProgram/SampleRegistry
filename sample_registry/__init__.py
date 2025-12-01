import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Optional

__version__ = "1.3.0"


# Doesn't include "NA" because that's what we fill in for missing values
NULL_VALUES: list[Optional[str]] = [
    None,
    "",
    "null",
    "NULL",
    "None",
    "none",
    "NONE",
    "N/A",
    "n/a",
    "na",
]


def sample_registry_version():
    sys.stderr.write(__version__)


try:
    SQLALCHEMY_DATABASE_URI = os.environ["SAMPLE_REGISTRY_DB_URI"]
except KeyError:
    sys.stdout.write(
        "Missing database connection information in environment, using test SQLite database\n"
    )
    db_path = Path(__file__).parent.parent.resolve() / "sample_registry.sqlite3"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///file:{db_path}?mode=ro&uri=true"


if "PYTEST_VERSION" in os.environ:
    # Set SQLALCHEMY_DATABASE_URI to an in-memory SQLite database for testing
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

# Create database engine
engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False)

# Create database session
Session = sessionmaker(bind=engine)
session = Session()
