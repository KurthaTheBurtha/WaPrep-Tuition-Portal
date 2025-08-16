#!/bin/bash

echo "Running migrations on staging environment..."

# Set environment variables
export DJANGO_SETTINGS_MODULE=tuition.settings_staging
export DEBUG=true

# Run migrations
python manage.py migrate --noinput

# Show migration status
python manage.py showmigrations

echo "Migrations completed!" 