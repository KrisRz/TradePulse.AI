# Multi-stage Dockerfile for TradePulse.AI Backend
# Optimized for production deployment to AWS App Runner

# --- Build Stage ---
FROM python:3.11-slim AS build

# Set environment variables for build efficiency
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY app/backend/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/backend/ /app/

# --- Runtime Stage ---
FROM python:3.11-slim AS runtime

# Set production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    ENV=production \
    HOST=0.0.0.0 \
    PORT=9002

# Install runtime system dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r tradepulse && useradd -r -g tradepulse tradepulse

WORKDIR /app

# Copy Python packages from build stage
COPY --from=build /usr/local /usr/local

# Copy application code from build stage
COPY --from=build /app /app

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/data && \
    chown -R tradepulse:tradepulse /app

# Switch to non-root user
USER tradepulse

# Health check endpoint for App Runner
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://127.0.0.1:9002/health || exit 1

# Expose the application port
EXPOSE 9002

# Start command - uvicorn with production settings
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9002", "--workers", "1", "--loop", "uvloop", "--http", "httptools", "--access-log", "--log-level", "info"]
