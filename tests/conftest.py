import os
import tempfile

import pytest
import sqlite3
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner

from rav2 import create_app
from rav2.models import db

with open(os.path.join(os.path.dirname(__file__), "data.sql"), "rb") as f:
    _data_sql = f.read().decode("utf8")


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        }
    )

    with app.app_context():
        db.create_all()
        sqlite3.connect(db_path).cursor().executescript(_data_sql)

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    with app.app_context():
        with app.test_client() as c:
            c.get("/")
            yield c


@pytest.fixture
def user_client(client: FlaskClient) -> FlaskClient:
    client.post("/login", data={"username": "test", "password": "test"})
    yield client


@pytest.fixture
def runner(app: Flask) -> FlaskCliRunner:
    return app.test_cli_runner()
