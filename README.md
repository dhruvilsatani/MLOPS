# MLOps Pipeline Implementation

An end-to-end MLOps pipeline for a RandomForest classifier on the Iris dataset — built to satisfy the thesis proposal's objectives, then extended beyond the thesis into something closer to how a real team would run it: infrastructure as code, a hardened container and cluster, GitOps deployment, observability with alerting, and a production-style MLflow tracking server.

The model itself is deliberately simple. The point of this project is everything around it — packaging, deploying, monitoring, and shipping changes to a model safely and repeatably.

## Project Structure

**Application**
- `train.py` — trains a RandomForest classifier on the Iris dataset with `scikit-learn`. Optional Gaussian noise via `--add-noise` (off by default). Logs each run to MLflow (params, metrics, model) unless `--no-tracking` is passed.
- `app.py` — FastAPI server exposing `/predict`, `/health`, and Prometheus metrics at `/metrics`, plus optional API-key auth.
- `requirement-prod.txt` / `requirements-dev.txt` — production and development dependency sets.
- `Dockerfile` — multi-stage build for the app image (non-root user, read-only-friendly, `HEALTHCHECK`).
- `.dockerignore` — keeps git history, caches, and docs out of the build context.
- `tests/` — pytest suite exercising the API in-process via `TestClient`.
- `test_api.py` — smoke/latency check against a running server.

**Infrastructure (Terraform, `terraform/`)**
- `vpc.tf` — VPC, subnets, route tables, internet gateway.
- `eks.tf` — Kubernetes cluster and node group.
- `ecr.tf` — container registries for the app image and the MLflow server image.
- `alb.tf` — application load balancer and target group.
- `iam.tf` — IAM roles for the cluster and nodes.
- `mlflow.tf` — the MLflow backend: an S3 bucket for model artifacts and an RDS Postgres instance for run metadata.
- `backend-setup.tf` — remote state (S3 + DynamoDB lock table).

This infrastructure is built and tested against [Floci](https://floci.io), a local AWS emulator, before it would ever run against a real account — RDS and S3 behave like the real services; a few pieces (like the ALB) are API-faithful only.

**Deployment (`k8s/ml-app-chart/`, a Helm chart)**
- `templates/deployment.yaml`, `service.yaml` — the FastAPI app, running as 2 replicas with a rolling update strategy (`maxUnavailable: 0`) for zero-downtime deploys.
- `templates/ingress.yaml`, `grafana-ingress.yaml` — NGINX Ingress routing for the app and for Grafana.
- `templates/mlflow-deployment.yaml`, `mlflow-service.yaml` — the MLflow tracking server, backed by the Postgres/S3 setup from `mlflow.tf`.
- `templates/servicemonitor.yaml`, `prometheusrule.yaml` — Prometheus scrape config and alert rules for the app.
- `values.yaml` — image tags, resource limits, ingress host, monitoring toggles.
- `k8s/argocd-application.yaml` — the ArgoCD Application that watches this chart in Git and syncs it to the cluster.
- `mlflow-server/Dockerfile` — a custom MLflow server image (the official one lacks `psycopg2-binary` and `boto3`, needed for Postgres and S3).

**CI/CD**
- `.github/workflows/deploy.yml` — lints, trains, tests, builds a multi-arch image, pushes it, and commits the new image tag back into `values.yaml` so ArgoCD picks it up.

## Endpoints
- `GET /` — web UI with sliders for the flower measurements. Open `http://localhost:8000/`.
- `GET /api` — machine-readable service banner (JSON).
- `GET /health` — `200` once the model is loaded, `503` otherwise. Used by the container `HEALTHCHECK` and the Kubernetes probes.
- `GET /metrics` — Prometheus metrics (request count, latency, error rate).
- `POST /predict` — predicts the species (**Setosa**, **Versicolor**, or **Virginica**) from `sepal_length`, `sepal_width`, `petal_length`, `petal_width` (cm, must be positive).

## Web UI
A lightweight frontend lives in `static/index.html`, served at `/`. Adjust the measurements, click **Classify**, see the prediction. **Reset** returns to a sample Setosa flower. If `API_KEY` is set, expand **Advanced: API key** and paste it there.

### API-key auth (optional)
Off by default so local development stays frictionless. Set `API_KEY` to require a matching `x-api-key` header on `/predict`; requests without it get `401`.

```bash
export API_KEY="your-secret"
curl -X POST http://localhost:8000/predict \
  -H "x-api-key: your-secret" -H "Content-Type: application/json" \
  -d '{"sepal_length":5.1,"sepal_width":3.5,"petal_length":1.4,"petal_width":0.2}'
```

## Prerequisites

1. **Docker Desktop** (or Docker engine)
2. **kubectl**, and either **Minikube** or a **k3s** cluster (Floci provisions one for local AWS-style testing)
3. **Terraform** (for provisioning infrastructure)
4. **Python 3.9+**
5. **Helm** and **ArgoCD** (for the GitOps deployment path)

## Local Development & Training

```bash
pip install -r requirements-dev.txt
python train.py
uvicorn app:app --reload
```

Test the API at `http://localhost:8000/docs`.

## Experiment Tracking (MLflow)

Two ways to run this, depending on what you're doing.

**Quick local tracking** — every `python train.py` run logs to a local `mlruns/` store under the `iris-classifier` experiment (hyperparameters, `test_accuracy`, `cv_accuracy_mean`, `cv_accuracy_std`, and the model artifact). View it with:
```bash
mlflow ui
```
Tracking is best-effort: if MLflow isn't installed or logging fails, the model still trains and saves to `model/model.pkl`. To skip tracking entirely (used by the Docker build and CI):
```bash
python train.py --no-tracking
```

**Production tracking server** — a real MLflow server (`mlflow-server/`), backed by Postgres (run metadata) and S3 (model artifacts), deployed the same way as the app: via the Helm chart and ArgoCD. Once it's running in the cluster:
```bash
kubectl port-forward svc/mlflow-server 5001:5000
MLFLOW_TRACKING_URI=http://localhost:5001 python train.py
```
This is what makes runs comparable across a team instead of stuck on one laptop.

## Containerization (Docker)

```bash
docker build -t ml-app:latest .
docker run -d -p 8000:8000 ml-app:latest
```
The image trains the model during the build so the shipped artifact is always consistent with the code that built it.

## Infrastructure (Terraform + Floci)

```bash
cd terraform
terraform init
terraform apply
```
This provisions the VPC, cluster, ECR repositories, ALB, IAM roles, and the MLflow S3 bucket and RDS instance — against Floci locally, or a real AWS account with the same files.

## Deployment (Helm + ArgoCD)

The cluster's desired state lives entirely in `k8s/ml-app-chart/` in Git — nothing is applied by hand in normal operation.

```bash
kubectl apply -f k8s/argocd-application.yaml
```
ArgoCD then watches the chart and syncs it to the cluster. To render the chart locally without deploying, for a sanity check:
```bash
helm template k8s/ml-app-chart
```

For local testing without the full GitOps loop, the chart can also be installed directly:
```bash
helm install ml-app k8s/ml-app-chart
```

## Observability

Prometheus scrapes `/metrics` on the app (config in `templates/servicemonitor.yaml`); Grafana visualizes it. Alert rules (`templates/prometheusrule.yaml`) cover the app being down, an elevated error rate on `/predict`, and pods restarting too often — wired to a Discord webhook via Alertmanager.

## Testing & Evaluation

```bash
pytest
```
Trains a model into a temp dir and exercises the API in-process — no server needs to be running.

```bash
python test_api.py
```
End-to-end latency/smoke check against a running server or Kubernetes service.

## CI/CD

`.github/workflows/deploy.yml`, triggered on every push to `main`:
1. Lints the code.
2. Trains the model (`--no-tracking`, so CI produces no `mlruns/` artifacts) and runs the test suite.
3. Builds and pushes a multi-arch Docker image, tagged with the commit SHA.
4. Writes that tag into `k8s/ml-app-chart/values.yaml` and commits it back to the repo.

ArgoCD picks up that commit and rolls the new version out — so shipping a change is: push code, and everything after that is automatic.
