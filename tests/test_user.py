import io
import base64

from flask import g, session, url_for
from flask.testing import FlaskClient

img_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="


def test_index(user_client: FlaskClient):
    response = user_client.get(url_for("index"))
    assert session["user_id"] == 1
    assert g.user.id == 1
    assert b"Logged in as test" in response.data
    assert repr(g.user)
    assert repr(g.user.avatars[0])


def test_anon_user(client: FlaskClient):
    response = client.get(url_for("user"))
    assert response.status_code == 302


def test_user(user_client: FlaskClient):
    response = user_client.get(url_for("user"))
    assert response.status_code == 200


def test_toggle(user_client: FlaskClient):
    response = user_client.get("/toggle?avatar_id=1")
    assert response.status_code == 302

    response = user_client.get("/toggle?avatar_id=1&ajax=yes")
    assert response.status_code == 200
    assert response.data == b"yes"

    response = user_client.get("/toggle?avatar_id=1&ajax=yes")
    assert response.status_code == 200
    assert response.data == b"no"


def test_delete(user_client: FlaskClient):
    # test's avatar
    response = user_client.get("/delete?avatar_id=1")
    assert response.status_code == 302

    # test2's avatar
    response = user_client.get("/delete?avatar_id=3")
    assert response.status_code == 404


def test_settings(user_client: FlaskClient):
    response = user_client.post(
        url_for("settings"),
        data={"message": "Hello!", "email": ""},
    )
    assert response.status_code == 302


def test_upload(user_client: FlaskClient):
    response = user_client.post(
        url_for("upload"),
        data={"avatar_data": (io.BytesIO(base64.b64decode(img_data)), "test.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302


def test_upload_long(user_client: FlaskClient):
    response = user_client.post(
        url_for("upload"),
        data={"avatar_data": (io.BytesIO(base64.b64decode(img_data)), "a" * 100)},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
