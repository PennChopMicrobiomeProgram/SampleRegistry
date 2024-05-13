import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

__version__ = "0.1.0"

try:
    db_host = os.environ["DB_HOST"]
    db_user = os.environ["DB_USER"]
    db_name = os.environ["DB_NAME"]
    db_pswd = os.environ["DB_PSWD"]
    SQLALCHEMY_DATABASE_URI = f"postgresql://{db_user}:{db_pswd}@{db_host}/{db_name}"
except KeyError:
    # For development purposes, use a SQLite db prefilled with some demo data
    sys.stderr.write("Missing database connection information in environment, using test SQLite database\n")
    sys.stderr.write(f"DB_HOST: {os.environ.get('DB_HOST')}\nDB_USER: {os.environ.get('DB_USER')}\nDB_NAME: {os.environ.get('DB_NAME')}\nDB_PSWD: {os.environ.get('DB_PSWD')}\n")
    SQLALCHEMY_DATABASE_URI = "sqlite:////home/ctbus/Penn/SampleRegistry/sample_registry.sqlite3"

# Create database engine
engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False)

# Create database session
Session = sessionmaker(bind=engine)
session = Session()
