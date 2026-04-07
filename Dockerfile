FROM python:3.11

WORKDIR /app

# Install system deps
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY server/requirements.txt .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Fix import paths
ENV PYTHONPATH=/app

# Move to server folder
WORKDIR /app/server

# Health check
HEALTHCHECK CMD curl -f http://localhost:8000/reset || exit 1

# Run server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]