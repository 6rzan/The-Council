# The Council — container image (T046, P3 deployment bonus).
# Runs the FastAPI web app directly via uvicorn (no browser auto-open; the
# launcher's local-only 127.0.0.1 binding is overridden to 0.0.0.0:$PORT for
# Cloud Run). GOOGLE_API_KEY is supplied at runtime as an env/secret, never
# baked into the image (.dockerignore excludes .env).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install pinned dependencies first (better layer caching).
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install the package (editable, no extra deps).
COPY pyproject.toml ./
COPY src ./src
RUN pip install -e . --no-deps

ENV PORT=8080
EXPOSE 8080

# Cloud Run expects 0.0.0.0 and the port in $PORT.
CMD ["sh", "-c", "uvicorn council.web.server:create_app --factory --host 0.0.0.0 --port ${PORT:-8080}"]
