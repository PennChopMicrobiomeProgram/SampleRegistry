import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Optional

__version__ = "1.4.1"


# Define archive root path
ARCHIVE_ROOT = Path(
    os.environ.get("SAMPLE_REGISTRY_ARCHIVE_ROOT", "/mnt/isilon/microbiome/")
)
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

SQLALCHEMY_DATABASE_URI = os.environ.get("SAMPLE_REGISTRY_DB_URI")
if SQLALCHEMY_DATABASE_URI is None:
    sys.stdout.write(
        "SAMPLE_REGISTRY_DB_URI not defined in environment, "
        "using in-memory SQLite database\n")
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

engine = create_engine(SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()
