from rav2 import create_app


def test_config():
    assert not create_app().testing
    assert create_app({"TESTING": True}).testing


def test_hello(client):
    response = client.get("/")
    assert response.data.startswith(b"<html>")
