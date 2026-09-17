"""Unit tests for the FastAPI app using the in-process TestClient.

These tests train a real model into a temp dir, point the app at it via the
MODEL_PATH env var, and exercise the app through its lifespan handler so the
model is loaded exactly like it would be in production.
"""
import importlib
import os

import pytest
from fastapi.testclient import TestClient

import train


VALID_PAYLOAD = {
    "sepal_length": 5.1,
    "sepal_width": 3.5,
    "petal_length": 1.4,
    "petal_width": 0.2,
}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    # Train a clean model into a temp location and point the app at it.
    model_dir = tmp_path_factory.mktemp("model")
    model_path = str(model_dir / "model.pkl")

    train.MODEL_DIR = str(model_dir)
    train.MODEL_PATH = model_path
    train.train(add_noise=False, track=False)

    os.environ["MODEL_PATH"] = model_path
    os.environ.pop("API_KEY", None)

    import app as app_module
    importlib.reload(app_module)

    with TestClient(app_module.app) as c:
        yield c


def test_home_serves_ui(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Iris Flower Classifier" in resp.text


def test_api_banner(client):
    resp = client.get("/api")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["model_loaded"] is True


def test_predict_setosa(client):
    resp = client.post("/predict", json=VALID_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["prediction"] == 0
    assert body["predicted_class"] == "Setosa"


def test_predict_virginica(client):
    resp = client.post(
        "/predict",
        json={
            "sepal_length": 6.9,
            "sepal_width": 3.1,
            "petal_length": 5.4,
            "petal_width": 2.1,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["predicted_class"] == "Virginica"


def test_predict_rejects_non_positive(client):
    bad = dict(VALID_PAYLOAD, sepal_length=-1.0)
    resp = client.post("/predict", json=bad)
    assert resp.status_code == 422


def test_predict_rejects_missing_field(client):
    bad = {"sepal_length": 5.1, "sepal_width": 3.5}
    resp = client.post("/predict", json=bad)
    assert resp.status_code == 422
