# backend/Dockerfile
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

FROM base AS runtime
COPY --from=builder /install /usr/local

# Copy the application package, Alembic config and migrations. Keeping the
# `app` package under /app/app preserves `import app...` and lets the
# entrypoint run `alembic upgrade head` (alembic.ini + migrations/ required).
COPY app /app/app
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations

# Persistent volumes mount here (WAL db + media). Non-root for least privilege.
RUN useradd -m -u 10001 appuser && mkdir -p /app/data /app/media && chown -R appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz').status==200 else 1)"

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
