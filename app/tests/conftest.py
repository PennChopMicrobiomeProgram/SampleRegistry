import pytest
from app.app import app as flask_app
from app.app import db
from sample_registry import SQLALCHEMY_DATABASE_URI, engine, session
from sample_registry.db import create_test_db
from sample_registry.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture()
def app():
    flask_app.config.update({
        "TESTING": True,
    })

    #db.init_app(flask_app)

    #with flask_app.app_context():
    Base.metadata.create_all(engine)

    create_test_db(session)

    yield flask_app

    # clean up / reset resources here


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()