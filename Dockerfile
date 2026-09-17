FROM python:3.9-slim AS builder 


# Don't buffer stdout/stderr; no .pyc files.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app


# Install dependencies first for better layer caching.
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy source code.
COPY . .

# Train model during build so the image ships with a ready model.
RUN python train.py --no-tracking

FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app


COPY --from=builder /app/model/model.pkl  ./model/model.pkl
COPY app.py .
COPY static ./static/
COPY requirement-prod.txt .

RUN pip install -r requirement-prod.txt

# Create and switch to a non-root user for runtime hardening.
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

RUN chown -R appuser:appgroup /app


USER appuser

EXPOSE 8000

# Container-level health check hitting the app's /health endpoint.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)" || exit 1

# Run FastAPI app.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
