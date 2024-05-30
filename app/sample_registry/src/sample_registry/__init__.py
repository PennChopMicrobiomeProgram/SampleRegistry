import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

__version__ = "0.1.0"


def sample_registry_version():
    sys.stderr.write(__version__)


print({k: v for k, v in os.environ.items() if "PYTEST" in k})

if "PYTEST_VERSION" in os.environ:
    # Set SQLALCHEMY_DATABASE_URI to an in-memory SQLite database for testing
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
else:
    try:
        db_host = os.environ["DB_HOST"]
        db_user = os.environ["DB_USER"]
        db_name = os.environ["DB_NAME"]
        db_pswd = os.environ["DB_PSWD"]
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql://{db_user}:{db_pswd}@{db_host}/{db_name}"
        )
    except KeyError:
        # For development purposes, use a SQLite db prefilled with some demo data
        sys.stdout.write(
            "Missing database connection information in environment, using test SQLite database\n"
        )
        sys.stdout.write(
            f"DB_HOST: {os.environ.get('DB_HOST')}\nDB_USER: {os.environ.get('DB_USER')}\nDB_NAME: {os.environ.get('DB_NAME')}\nDB_PSWD: {os.environ.get('DB_PSWD')}\n"
        )
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{Path(__file__).parent.parent.parent.parent.parent.resolve()}/sample_registry.sqlite3"

print(SQLALCHEMY_DATABASE_URI)

# Create database engine
engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False)

# Create database session
Session = sessionmaker(bind=engine)
session = Session()
