FROM python:3.11-slim

RUN pip install --no-cache-dir mlflow==3.15.2 psycopg2-binary boto3

RUN useradd --create-home --uid 1000 mlflow
USER mlflow

EXPOSE 5000

CMD ["sh", "-c", "mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri \"$MLFLOW_BACKEND_STORE_URI\" --artifacts-destination \"$MLFLOW_ARTIFACTS_DESTINATION\" --serve-artifacts"]