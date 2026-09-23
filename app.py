import os
from contextlib import asynccontextmanager

import joblib
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from prometheus_fastapi_instrumentator import Instrumentator


MODEL_PATH = os.getenv("MODEL_PATH", "model/model.pkl")
CLASS_NAMES = ["Setosa", "Versicolor", "Virginica"]

# Directory holding the web UI (index.html + any assets).
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# Optional API-key auth. If API_KEY is unset, /predict stays open (dev mode).
API_KEY = os.getenv("API_KEY")

# Holds runtime state (populated on startup via the lifespan handler).
state = {"model": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.path.exists(MODEL_PATH):
        state["model"] = joblib.load(MODEL_PATH)
        print(f"Model loaded successfully from {MODEL_PATH}.")
    else:
        print(f"Model file not found at {MODEL_PATH}. Train the model first (python train.py).")
    yield
    state["model"] = None


app = FastAPI(
    title="MLOps Pipeline API",
    description="API for Iris Classification",
    version="1.0",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app)

# Mount the static directory so extra assets (css/js/images) are served under /static.
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class IrisData(BaseModel):
    # gt=0 rejects negative/zero measurements, which are physically impossible.
    sepal_length: float = Field(..., gt=0, description="Sepal length in cm")
    sepal_width: float = Field(..., gt=0, description="Sepal width in cm")
    petal_length: float = Field(..., gt=0, description="Petal length in cm")
    petal_width: float = Field(..., gt=0, description="Petal width in cm")


class PredictionResponse(BaseModel):
    prediction: int
    predicted_class: str


def require_api_key(x_api_key: str = Header(default=None)):
    """Enforce the API key only when one is configured via the API_KEY env var."""
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key."
        )


@app.get("/")
def home():
    """Serve the web UI. Falls back to a JSON banner if the UI is missing."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Welcome to the MLOps Pipeline API!", "status": "running"}


@app.get("/api")
def api_banner():
    """Machine-readable banner (the old / response)."""
    return {"message": "Welcome to the MLOps Pipeline API!", "status": "running"}


@app.get("/health")
def health():
    """Readiness/liveness probe target. 503 until the model is loaded."""
    if state["model"] is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    return {"status": "ok", "model_loaded": True}




@app.post("/predict", response_model=PredictionResponse, dependencies=[Depends(require_api_key)])
def predict(data: IrisData):
    model = state["model"]
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded.")

    features = [[data.sepal_length, data.sepal_width, data.petal_length, data.petal_width]]
    try:
        pred_val = int(model.predict(features)[0])
        return PredictionResponse(prediction=pred_val, predicted_class=CLASS_NAMES[pred_val])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
