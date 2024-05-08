import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sample_registry.models import Base

try:
    db_host = os.environ.get("DB_HOST")
    db_user = os.environ.get("DB_USER")
    db_name = os.environ.get("DB_NAME")
    db_pswd = os.environ.get("DB_PSWD")
    SQLALCHEMY_DATABASE_URI = f"postgresql://{db_user}:{db_pswd}@{db_host}/{db_name}"
except KeyError:
    # For development purposes, use a SQLite prefilled with some demo data
    sys.stderr.write("No database connection information found in environment, using test SQLite database\n")
    SQLALCHEMY_DATABASE_URI = "sqlite:///sample_registry.db"

# Create database engine
engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False)

# Create database session
Session = sessionmaker(bind=engine)
session = Session()

if "sqlite:///" in SQLALCHEMY_DATABASE_URI:
    if not Path("sample_registry.db").exists():
        Base.metadata.create_all(engine)
        