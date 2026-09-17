"""Tests for the optional API-key auth on /predict."""
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
def secured_client(tmp_path_factory):
    model_dir = tmp_path_factory.mktemp("model_auth")
    model_path = str(model_dir / "model.pkl")

    train.MODEL_DIR = str(model_dir)
    train.MODEL_PATH = model_path
    train.train(add_noise=False, track=False)

    os.environ["MODEL_PATH"] = model_path
    os.environ["API_KEY"] = "secret-key"

    import app as app_module
    importlib.reload(app_module)

    with TestClient(app_module.app) as c:
        yield c

    os.environ.pop("API_KEY", None)


def test_predict_requires_key(secured_client):
    resp = secured_client.post("/predict", json=VALID_PAYLOAD)
    assert resp.status_code == 401


def test_predict_rejects_wrong_key(secured_client):
    resp = secured_client.post(
        "/predict", json=VALID_PAYLOAD, headers={"x-api-key": "nope"}
    )
    assert resp.status_code == 401


def test_predict_accepts_valid_key(secured_client):
    resp = secured_client.post(
        "/predict", json=VALID_PAYLOAD, headers={"x-api-key": "secret-key"}
    )
    assert resp.status_code == 200
    assert resp.json()["predicted_class"] == "Setosa"
