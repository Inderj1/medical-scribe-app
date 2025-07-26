#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h $DATABASE_HOST -p $DATABASE_PORT -U $DATABASE_USER; do
  sleep 2
done

# Run database migrations
echo "Running database migrations..."
cd /app/backend
alembic upgrade head

# Create default admin user if not exists
python create_admin_user.py || true

# Start the application
echo "Starting application..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4