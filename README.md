# MLOps Pipeline Implementation

This project implements an end-to-end scalable and secure MLOps pipeline using Docker and Kubernetes, built for classifying iris flowers using a RandomForest model. It satisfies all objectives mentioned in the thesis proposal.

## Project Structure
- `train.py`: The machine learning training script using `scikit-learn`. Trains a RandomForest classifier on the classic Iris dataset. Optional Gaussian noise can be added to the features via `--add-noise` (off by default). Each run is logged to MLflow (params, metrics, model) unless `--no-tracking` is passed.
- `app.py`: FastAPI server serving the trained model via a `/predict` endpoint, plus a `/health` probe and optional API-key auth.
- `requirements.txt`: Python package dependencies.
- `Dockerfile`: Instructions to containerize the ML application (runs as a non-root user, includes a HEALTHCHECK).
- `.dockerignore`: Keeps build context (git history, caches, docs) out of the image.
- `k8s/deployment.yaml`: Kubernetes Deployment with liveness/readiness probes and a hardened securityContext.
- `k8s/service.yaml`: Kubernetes Service for exposing the deployment.
- `.github/workflows/deploy.yml`: GitHub Actions pipeline for CI/CD automation (installs, trains, runs the pytest suite, builds and pushes the image).
- `tests/`: pytest unit tests exercising the API in-process via `TestClient`.
- `test_api.py`: Python script for evaluating real-time prediction performance against a running server.

## Endpoints
- `GET /` — the web UI (a simple page with sliders for the flower measurements). Open `http://localhost:8000/` in a browser.
- `GET /api` — machine-readable service banner (JSON).
- `GET /health` — returns `200` once the model is loaded, `503` otherwise. Used by the container HEALTHCHECK and the Kubernetes probes.
- `POST /predict` — predicts the iris species and returns the class index plus name (**Setosa**, **Versicolor**, or **Virginica**). Expects four fields: `sepal_length`, `sepal_width`, `petal_length`, `petal_width` (all in cm, must be positive).

## Web UI
A lightweight frontend lives in `static/index.html` and is served automatically at `/`. Adjust the flower measurements, click **Classify**, and the predicted species appears. Use **Reset** to return to a classic Setosa sample. If the server has `API_KEY` set, expand **Advanced: API key** and paste the key there.

### API-key auth (optional)
Auth is off by default so local development stays frictionless. Set the `API_KEY` environment variable to require callers to send a matching `x-api-key` header on `/predict`; requests without it (or with the wrong key) get `401`.

```bash
export API_KEY="your-secret"
curl -X POST http://localhost:8000/predict \
  -H "x-api-key: your-secret" -H "Content-Type: application/json" \
  -d '{"sepal_length":5.1,"sepal_width":3.5,"petal_length":1.4,"petal_width":0.2}'
```

## Prerequisites

1.  **Docker Desktop** (or Docker engine)
2.  **Minikube** and **kubectl** (for local Kubernetes testing)
3.  **Python 3.9+**

## Step 1: Local Development & Training
1. Create a virtual environment and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Train the model:
   ```bash
   python train.py
   ```
   *This saves the model in the `model/` directory.*
3. Run the FastAPI dev server:
   ```bash
   uvicorn app:app --reload
   ```
4. Test the API at `http://localhost:8000/docs`.

## Experiment Tracking (MLflow)
Every `python train.py` run is logged to a local MLflow tracking store (an `mlruns/` directory) under the **`iris-classifier`** experiment. Each run records the hyperparameters (`n_estimators`, `max_depth`, `random_state`, `add_noise`, `noise_std`), the metrics (`test_accuracy`, `cv_accuracy_mean`, `cv_accuracy_std`), and the trained model as an artifact.

View and compare runs in the MLflow UI:
```bash
mlflow ui
```
Then open `http://localhost:5000`.

Tracking is best-effort and non-blocking: if MLflow isn't installed, or logging fails, the model is still trained and saved to `model/model.pkl` exactly as before. To skip tracking entirely (used by the Docker build and CI so no `mlruns/` artifacts are produced), run:
```bash
python train.py --no-tracking
```

## Step 2: Containerization (Docker)
1. Build the Docker image:
   ```bash
   docker build -t ml-app:latest .
   ```
   *Note: This automatically trains the model during the image build process to guarantee consistency.*
2. Run the container:
   ```bash
   docker run -d -p 8000:8000 ml-app:latest
   ```

## Step 3: Kubernetes Orchestration (Minikube)
1. Start minikube:
   ```bash
   minikube start
   ```
2. Apply the Kubernetes deployment and service:
   ```bash
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml
   ```
3. Expose the service locally using minikube:
   ```bash
   minikube service ml-app-service
   ```
   *(Or run `minikube tunnel` in a background terminal, which exposes the LoadBalancer Service natively).*

## Step 4: Testing & Evaluation
Run the unit tests (they train a model into a temp dir and exercise the API in-process, so no server needs to be running):
```bash
pytest
```

For an end-to-end latency/smoke check against a running server or Kubernetes service:
```bash
python test_api.py
```
This tests correctness, status codes, and latency (response time).

## Step 5: Continuous Integration / Continuous Deployment (CI/CD)
Using GitHub Actions, you can push this code to a GitHub repo. The `.github/workflows/deploy.yml` automates:
1. Installing dependencies.
2. Training the Model (with `--no-tracking`, so CI produces no `mlruns/` artifacts).
3. Logging in to Docker Hub (set your credentials via Secrets).
4. Building and Pushing the final image to Docker Hub, which can then be rolled out into Kubernetes.
