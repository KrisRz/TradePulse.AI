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

# Copy application code with proper structure
COPY . /tmp/project
RUN mkdir -p /app && cp -r /tmp/project/app /app/ && rm -rf /tmp/project

# --- Runtime Stage ---
FROM python:3.11-slim AS runtime

# Set production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    ENVIRONMENT=production \
    HOST=0.0.0.0 \
    PORT=9002

# Install runtime system dependencies (including ML libraries deps)
RUN apt-get update && apt-get install -y \
    curl \
    libgomp1 \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r tradepulse && useradd -r -g tradepulse tradepulse

WORKDIR /app

# Copy Python packages from build stage
COPY --from=build /usr/local /usr/local

# Copy application code from build stage (with proper structure)
COPY --from=build /app /app

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/data && \
    chown -R tradepulse:tradepulse /app

# Switch to non-root user
USER tradepulse

# Set production environment (can be overridden by App Runner)
ENV ENVIRONMENT=production

# Health check endpoint for App Runner
# Increased start-period for model loading (2 min grace period)
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://127.0.0.1:9002/health || exit 1

# Expose the application port
EXPOSE 9002

# Start command - properly reference main module in app/backend
CMD ["python", "-m", "uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "9002", "--workers", "1"]

# Cache bust for force rebuild - LAYER 7 FIX + DAY TRADING FLEXIBILITY
ENV CACHE_BUST=20251010_LAYER7_FIX_DAYTRADING_OPTIMIZED
