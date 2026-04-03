FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements FIRST (for caching)
COPY server/requirements.txt .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# 🔥 Copy ENTIRE project (IMPORTANT)
COPY . .

# 🔥 Make root visible for imports (models.py, client.py etc)
ENV PYTHONPATH=/app

# Move into server folder for running app
WORKDIR /app/server

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]