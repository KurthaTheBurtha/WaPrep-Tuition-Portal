#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running database migrations..."
export DJANGO_SETTINGS_MODULE=tuition.settings_production
python manage.py migrate --noinput

echo "Creating default admin user if it doesn't exist..."
python manage.py create_admin --first_name "Admin" --last_name "User" --email "admin@waprep.org" --password "Admin123!@#" || echo "Admin user already exists or error occurred"

echo "Build completed successfully!"