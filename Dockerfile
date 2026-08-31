# NetPulse Production Container Image
FROM python:3.11-slim

WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests
COPY requirements.txt pyproject.toml /app/

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Expose HTTP REST & WebSocket API port
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV NETPULSE_HOST=0.0.0.0
ENV NETPULSE_PORT=8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/api/status || exit 1

# Start NetPulse Server Entrypoint
ENTRYPOINT ["python", "server/main.py", "--host", "0.0.0.0", "--port", "8080"]
