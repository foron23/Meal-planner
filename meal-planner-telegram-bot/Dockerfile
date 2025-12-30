# =============================================================================
# Meal Planner Telegram Bot - Dockerfile
# =============================================================================
# Multi-stage build for a lean production image
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:3.13-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Production
# -----------------------------------------------------------------------------
FROM python:3.13-slim as production

# Labels
LABEL maintainer="your-email@example.com"
LABEL description="Meal Planner Telegram Bot with LangGraph AI"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=appuser:appgroup src/ ./src/
COPY --chown=appuser:appgroup scripts/ ./scripts/
COPY --chown=appuser:appgroup tests/ ./tests/
COPY --chown=appuser:appgroup pyproject.toml ./
COPY --chown=appuser:appgroup README.md ./

# Create data directory for SQLite database
RUN mkdir -p /app/data && chown appuser:appgroup /app/data

# Switch to non-root user
USER appuser

# Create volume mount point for persistent data
VOLUME ["/app/data"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["python", "-m", "src.bot"]