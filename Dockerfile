FROM debian:bookworm-slim

WORKDIR /app

# Install Python + pip + curl
RUN apt-get update && \
    apt-get install -y python3 python3-pip curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY server/requirements.txt .

# Install dependencies
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy project files
COPY . .

# Fix imports
ENV PYTHONPATH=/app

# Move into server folder
WORKDIR /app/server

# Run FastAPI
CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]