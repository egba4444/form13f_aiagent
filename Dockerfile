# Multi-stage Dockerfile for Form 13F AI Agent
# Updated: 2025-11-22 - Added Qdrant API key authentication support
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
# Use CPU-only torch to reduce image size
RUN uv sync --frozen --no-dev

# Clean up unnecessary files to reduce image size
RUN find /app/.venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -name "*.pyc" -delete && \
    find /app/.venv -name "*.pyo" -delete && \
    find /app/.venv -type d -name "*.dist-info" -exec sh -c 'rm -rf "$1"/{RECORD,INSTALLER,WHEEL}' _ {} \; 2>/dev/null || true

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

# Activate virtual environment and run uvicorn
ENV PATH="/app/.venv/bin:$PATH"

# Default command - uses $PORT env var from Railway (defaults to 8000)
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
