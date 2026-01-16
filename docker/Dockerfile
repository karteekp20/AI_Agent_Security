# ============================================================================
# SENTINEL AI SECURITY - PRODUCTION DOCKERFILE
# Multi-stage build for optimized image size with Poetry
# ============================================================================

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.7.1
ENV POETRY_HOME=/opt/poetry
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_VIRTUALENVS_CREATE=true
ENV PATH="$POETRY_HOME/bin:$PATH"

RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies (without dev dependencies)
RUN poetry install --without dev --no-root

# Download spaCy model during build
RUN poetry run python -m spacy download en_core_web_sm

# Stage 2: Runtime
FROM python:3.11-slim as runtime

WORKDIR /app

# Install runtime dependencies (PostgreSQL client library + curl for healthcheck + pg_isready)
RUN apt-get update && apt-get install -y \
    libpq5 \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Poetry virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY sentinel/ ./sentinel/
COPY examples/ ./examples/
COPY migrations/ ./migrations/
COPY alembic.ini .
COPY pyproject.toml .
COPY README.md .

# Set PATH to use Poetry virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Copy and setup entrypoint script
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create non-root user
RUN useradd -m -u 1000 sentinel && chown -R sentinel:sentinel /app
USER sentinel

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose ports
# API server
EXPOSE 8000
# Prometheus metrics (future)
EXPOSE 9090

# Health check - test API endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set entrypoint to run migrations before starting app
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command (SaaS API server)
CMD ["python", "-m", "uvicorn", "sentinel.saas.server:app", "--host", "0.0.0.0", "--port", "8000"]
