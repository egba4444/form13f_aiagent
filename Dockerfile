# Multi-stage Dockerfile for Form 13F AI Agent
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./
COPY uv.lock ./
COPY src/ ./src/

# Install Python dependencies using uv sync (much faster than pip)
RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy uv-managed virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ ./src/
COPY schema/ ./schema/

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Create data directories
RUN mkdir -p data/raw data/processed data/cache && \
    chown -R appuser:appuser data/

USER appuser

# Expose FastAPI port
EXPOSE 8000

# Activate virtual environment and run uvicorn
ENV PATH="/app/.venv/bin:$PATH"

# Default command - Railway will override with railway.toml startCommand
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
