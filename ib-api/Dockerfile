# FastAPI wrapper for IB Gateway
# Production-ready Dockerfile with security best practices

FROM python:3.11-slim

# Environment settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (required for some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN addgroup --system app && adduser --system --ingroup app app

# Copy requirements first for layer caching
COPY --chown=app:app requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY --chown=app:app . .

# Switch to non-root user
USER app

# Expose API port
EXPOSE 8000

# Health check - use /ping which always returns 200 if server is running
# The /health endpoint may return 503 if IB Gateway isn't connected, but
# the API server itself is still functional and shouldn't be restarted
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ping')" || exit 1

# Run uvicorn server
# --proxy-headers: Trust X-Forwarded-* headers from Coolify's Traefik proxy
# --forwarded-allow-ips: Allow forwarded headers from any IP (behind proxy)
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
