import pytest
from flask import g, session, Flask
from flask.testing import FlaskClient, FlaskCliRunner

from rav2.models import db


def test_create(app: Flask, client: FlaskClient):
    response = client.post(
        "/create", data={"username": "a", "password1": "b", "password2": "b"}
    )
    assert response.headers["Location"] == "/user"

    with app.app_context():
        assert (
            db.session.execute(
                db.text("SELECT * FROM users WHERE name = 'a'"),
            ).fetchone()
            is not None
        )


@pytest.mark.parametrize(
    ("username", "password1", "password2", "message"),
    (
        ("", "", "", b"Username is required"),
        ("a", "", "", b"Password is required"),
        ("a", "b", "c", b"don&#39;t match"),
        ("test", "test", "test", b"already been taken"),
    ),
)
def test_create_validate_input(
    client: FlaskClient, username, password1, password2, message
):
    response = client.post(
        "/create",
        data={"username": username, "password1": password1, "password2": password2},
    )
    assert message in response.data


def test_login(client: FlaskClient):
    response = client.post("/login", data={"username": "test", "password": "test"})
    assert response.headers["Location"] == "/user"

    client.get("/")
    assert session["user_id"] == 1
    assert g.user.id == 1


@pytest.mark.parametrize(
    ("username", "password"),
    (
        ("a", "test"),
        ("test", "a"),
    ),
)
def test_login_validate_input(client: FlaskClient, username, password):
    response = client.post("/login", data={"username": username, "password": password})
    assert response.status_code == 404


def test_logout(app: Flask, client: FlaskClient) -> None:
    response = client.post("/login", data={"username": "test", "password": "test"})
    assert response.headers["Location"] == "/user"

    client.get("/")
    assert session["user_id"] == 1
    assert g.user.id == 1

    response = client.get(
        "/logout",
    )
    assert response.headers["Location"] == "/"

    client.get("/")
    assert "user_id" not in session
    assert g.user is None
