# Multi-stage Dockerfile for AMBOSS Screenshot Scraper
FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock ./

# Configure Poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY amboss/ ./amboss/

# Create necessary directories
RUN mkdir -p /app/secrets /app/captures /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV AMBOSS_COOKIE_PATH=/app/secrets/auth_state.json
ENV AMBOSS_DATABASE_PATH=/app/data/amboss_scraper.db
ENV AMBOSS_OUTPUT_DIR=/app/captures

# Create non-root user
RUN useradd -m -u 1000 scraper && \
    chown -R scraper:scraper /app

# Switch to non-root user
USER scraper

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; from amboss.db import init_database; asyncio.run(init_database())" || exit 1

# Default command
ENTRYPOINT ["poetry", "run", "amboss"] 