# Multi-stage build for Django + Vue
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install frontend dependencies
RUN npm install

# Copy frontend source
COPY frontend/ ./

# Build frontend
RUN npm run build

# Python stage
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/
COPY sherman/ ./sherman/
COPY manage.py .

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Expose port (Railway will set PORT env var)
EXPOSE 8000

# Run migrations and start server
# Railway sets PORT as environment variable
CMD python manage.py migrate && gunicorn backend.wsgi:application --bind 0.0.0.0:${PORT:-8000}

