FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model for PII detection
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY src/ ./src/
COPY policies/ ./policies/

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/notes

# Set Python path
ENV PYTHONPATH=/app

# Run as non-root user
RUN useradd -m -u 1000 synm && \
    chown -R synm:synm /app
USER synm

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application (deprecated - use mediator/Dockerfile instead)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
