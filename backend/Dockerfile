# ── MailPilot Backend ─────────────────────────────────
# Lightweight production image for the FastAPI backend.
# Usage: docker build -t mailpilot-backend .
# ──────────────────────────────────────────────────────
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── Install dependencies (cached layer) ──────────────
COPY pyproject.toml .
# Create a minimal app/__init__.py so hatchling can resolve the package
# during the dependency-install step (the real code is copied next).
RUN mkdir -p app && touch app/__init__.py && \
    pip install --no-cache-dir .

# ── Copy application code ────────────────────────────
COPY app/ app/

# ── Create data directory for SQLite ─────────────────
RUN mkdir -p /app/data

EXPOSE 8000

# Run with a single uvicorn worker (sufficient for personal use).
# For heavier loads, switch to gunicorn -k uvicorn.workers.UvicornWorker.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
