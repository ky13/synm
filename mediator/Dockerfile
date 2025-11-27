FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install (includes spaCy model)
COPY mediator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY mediator/app/ ./app/
COPY scripts/ ./scripts/

# Create data directory
RUN mkdir -p /app/data

# Run as non-root
RUN useradd -m -u 1000 mediator && \
    chown -R mediator:mediator /app
USER mediator

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
