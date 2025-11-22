# Single-stage Dockerfile for Form 13F AI Agent
# Updated: 2025-11-22 - Removed multi-stage to force cache invalidation
# Build version: 3.0 - EMERGENCY CACHE BUST
FROM python:3.11-slim

WORKDIR /app

# Install ALL dependencies (build + runtime) in one shot
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./
COPY uv.lock ./

# Install Python dependencies FIRST (before copying src/)
# This preserves caching for dependencies
RUN uv sync --frozen --no-dev

# FORCE CACHE INVALIDATION - timestamp changes every build
ARG CACHEBUST_V3=1
RUN echo "FORCE REBUILD v3: $(date +%s)" > /tmp/cachebust

# NOW copy application code - this layer will ALWAYS rebuild
COPY src/ ./src/
COPY schema/ ./schema/

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Create data directories
RUN mkdir -p data/raw data/processed data/cache && \
    chown -R appuser:appuser data/

USER appuser

# Activate virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8080

# Default command
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
