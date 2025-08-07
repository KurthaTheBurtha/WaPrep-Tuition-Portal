#!/bin/bash

# WaPrep Tuition Portal - Startup Script
# This script handles database migrations and starts the application

set -e  # Exit on any error

echo "🚀 Starting WaPrep Tuition Portal..."

# Check environment variables
echo "📋 Environment Check:"
echo "DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"
echo "DATABASE_URL: ${DATABASE_URL:0:20}..."  # Show first 20 chars for security
echo "DEBUG: $DEBUG"

# Wait for database to be ready (if using PostgreSQL)
if [[ $DATABASE_URL == postgresql://* ]]; then
    echo "⏳ Waiting for PostgreSQL database to be ready..."
    python manage.py wait_for_db --timeout=30
fi

# Run migrations with detailed output
echo "🗄️ Running database migrations..."
python manage.py run_migrations

# Show migration status
echo "📊 Migration Status:"
python manage.py showmigrations

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Start the application
echo "🌐 Starting Gunicorn server..."
exec gunicorn tuition.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120 