FROM python:3.10-bullseye

WORKDIR /app

# Install system deps (very minimal, stable image)
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Copy everything first (important for context)
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r server/requirements.txt

# Fix imports
ENV PYTHONPATH=/app

# Run from server directory
WORKDIR /app/server

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]