import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

__version__ = "1.0.4"


def sample_registry_version():
    sys.stderr.write(__version__)


if "PYTEST_VERSION" in os.environ:
    # Set SQLALCHEMY_DATABASE_URI to an in-memory SQLite database for testing
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
else:
    try:
        db_host = os.environ["SAMPLE_REGISTRY_DB_HOST"]
        db_user = os.environ["SAMPLE_REGISTRY_DB_USER"]
        db_name = os.environ["SAMPLE_REGISTRY_DB_NAME"]
        db_pswd = os.environ["SAMPLE_REGISTRY_DB_PSWD"]
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql://{db_user}:{db_pswd}@{db_host}/{db_name}"
        )
    except KeyError:
        # For development purposes, use a SQLite db prefilled with some demo data
        sys.stdout.write(
            "Missing database connection information in environment, using test SQLite database\n"
        )
        sys.stdout.write(
            f"SAMPLE_REGISTRY_DB_HOST: {os.environ.get('SAMPLE_REGISTRY_DB_HOST')}\nSAMPLE_REGISTRY_DB_USER: {os.environ.get('SAMPLE_REGISTRY_DB_USER')}\nSAMPLE_REGISTRY_DB_NAME: {os.environ.get('SAMPLE_REGISTRY_DB_NAME')}\nSAMPLE_REGISTRY_DB_PSWD: {os.environ.get('SAMPLE_REGISTRY_DB_PSWD')}\n"
        )
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{Path(__file__).parent.parent.parent.parent.parent.resolve()}/sample_registry.sqlite3"

print(SQLALCHEMY_DATABASE_URI)

# Create database engine
engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False)

# Create database session
Session = sessionmaker(bind=engine)
session = Session()
