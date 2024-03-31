from flask.testing import FlaskClient
from rav2.models import Avatar
from unittest.mock import patch


def test_favicon(client: FlaskClient):
    response = client.get("/favicon.ico")
    assert response.status_code == 200


def test_index(client: FlaskClient):
    response = client.get("/")
    assert response.status_code == 200


def test_manual(client: FlaskClient):
    response = client.get("/manual")
    assert response.status_code == 200


def test_gallery(client: FlaskClient):
    response = client.get("/gallery")
    assert response.status_code == 200


def test_user_gallery(client: FlaskClient):
    response = client.get("/test.html")
    assert response.status_code == 200

    response = client.get("/nobody.html")
    assert response.status_code == 404


def test_avatar(client: FlaskClient):
    with patch.object(Avatar, "data", "test"):
        response = client.get("/test.png")
        assert response.status_code == 200

        response = client.get("/nobody.png")
        assert response.status_code == 404

        response = client.get("/1873689aae9bd74e55dec440e10bc01c.png")
        assert response.status_code == 200

        response = client.get("/xxx3689aae9bd74e55dec440e10bcxxx.png")
        assert response.status_code == 404

        response = client.get("/1873689aae9bd74e55dec440e10bc01c/blah.png")
        assert response.status_code == 200

        response = client.get("/xxx3689aae9bd74e55dec440e10bcxxx/blah.png")
        assert response.status_code == 404
