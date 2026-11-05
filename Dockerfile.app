# Multi-stage Dockerfile for Application Under Test (AUT)
FROM python:3.10-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AUT_DB_FILE=/app/data/aut_database.sqlite

# Create directory for SQLite persistent database
RUN mkdir -p /app/data

# Copy project files
COPY app/ /app/app/
COPY requirements.txt /app/

# Install dependencies
RUN python -m pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

CMD ["python", "-m", "app.app"]
