# FROM python:3.9-slim
FROM python:3.9-slim-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data logs models

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Expose port (if web interface is added later)
# EXPOSE 8000

# Health check
HEALTHCHECK --interval=5m --timeout=3s \
  CMD sqlite3 /app/data/trading.db "SELECT 1" || exit 1

# Run the bot
CMD ["python", "run_bot.py"]
