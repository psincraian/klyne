# Frontend build stage
FROM node:20-slim AS frontend-builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source files needed for build
COPY tailwind.config.js ./
COPY src/static/css/input.css ./src/static/css/input.css
COPY src/templates/ ./src/templates/

# Build CSS
RUN npm run build

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENVIRONMENT=production

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser -m appuser

# Install system dependencies in a single layer
# Use --no-install-recommends and clean up in same layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set work directory
WORKDIR /app

# Copy only dependency files first for better caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies in a separate stage for better caching
# Use pre-compiled wheels when possible
RUN uv sync --frozen --no-dev

# Copy application code (this will be the layer that changes most often)
COPY . .

# Copy built CSS from frontend stage
COPY --from=frontend-builder /app/src/static/css/output.css ./src/static/css/output.css

# Create cache directory and change ownership in single layer
RUN mkdir -p /home/appuser/.cache && \
    chown -R appuser:appuser /app /home/appuser/.cache

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Simplified healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run the application
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]