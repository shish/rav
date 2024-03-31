import pytest
from flask import g, session, Flask
from flask.testing import FlaskClient, FlaskCliRunner

from rav2.models import db


@pytest.mark.parametrize(
    ("username", "password1", "password2", "error"),
    (
        ("a", "b", "b", None),
        ("", "", "", b"Username is required"),
        ("a", "", "", b"Password is required"),
        ("a", "b", "c", b"don&#39;t match"),
        ("test", "test", "test", b"already been taken"),
        ("TeSt", "test", "test", b"already been taken"),
        ("a" * 32, "aaaa", "aaaa", b"less than 32"),
    ),
)
def test_create(client: FlaskClient, username, password1, password2, error):
    response = client.post(
        "/create",
        data={"username": username, "password1": password1, "password2": password2},
    )
    if error:
        assert error in response.data
    else:
        assert response.headers.get("Location") == "/user"
        assert (
            db.session.execute(
                db.text(f"SELECT * FROM users WHERE name = '{username}'"),
            ).fetchone()
            is not None
        )


@pytest.mark.parametrize(
    ("username", "password", "ok"),
    (
        ("test", "test", True),  # exact match
        ("TeSt", "test", True),  # name should be case-insensitive
        ("a", "test", False),  # invalid name
        ("test", "a", False),  # invalid password
        ("test", "TeSt", False),  # password should be case-sensitive
    ),
)
def test_login(client: FlaskClient, username, password, ok):
    response = client.post("/login", data={"username": username, "password": password})
    if ok:
        assert response.headers.get("Location") == "/user"

        client.get("/user")
        assert session.get("user_id") == 1
        assert g.user.id == 1
    else:
        assert response.status_code == 404


def test_logout(app: Flask, client: FlaskClient) -> None:
    response = client.post("/login", data={"username": "test", "password": "test"})
    assert response.headers.get("Location") == "/user"

    client.get("/")
    assert session.get("user_id") == 1
    assert g.user.id == 1

    response = client.get(
        "/logout",
    )
    assert response.headers.get("Location") == "/"

    client.get("/")
    assert "user_id" not in session
    assert g.user is None
