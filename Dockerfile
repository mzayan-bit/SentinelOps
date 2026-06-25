# Stage 1: Builder
FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production
FROM python:3.10-slim

WORKDIR /app

# Install runtime system dependencies (required for OpenCV)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Setup environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Create a non-root user
RUN groupadd -r sentinel && useradd -r -g sentinel sentinel

# Copy application code
COPY . .

# Ensure the non-root user has ownership of the application directory and artifact storage paths
RUN mkdir -p artifacts/events artifacts/snapshots artifacts/reports config \
    && chown -R sentinel:sentinel /app

# Switch to non-root user
USER sentinel

# Expose the API port
EXPOSE 8000

# Production entrypoint using environment variables
CMD ["sh", "-c", "uvicorn app.api.app:app --host $HOST --port $PORT"]
