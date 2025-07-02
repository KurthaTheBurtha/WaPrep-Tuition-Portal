#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Setting Django settings module..."
export DJANGO_SETTINGS_MODULE=tuition.settings_production
echo "DJANGO_SETTINGS_MODULE set to: $DJANGO_SETTINGS_MODULE"

echo "Checking database connection..."
python manage.py check --database default

echo "Running database migrations..."
python manage.py migrate --noinput --verbosity=2

echo "Checking migration status..."
python manage.py showmigrations

echo "Creating default admin user if it doesn't exist..."
python manage.py create_admin --first_name "Admin" --last_name "User" --email "admin@waprep.org" --password "Admin123!@#" || echo "Admin user already exists or error occurred"

echo "Build completed successfully!"