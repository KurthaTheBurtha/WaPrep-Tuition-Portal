#!/usr/bin/env bash
# exit on error
set -o errexit

echo "=== WaPrep Tuition Portal Build Script ==="
echo "Installing dependencies..."

# Try to install psycopg3 first, fallback to psycopg2 if needed
echo "Installing PostgreSQL adapter..."
pip install psycopg[binary]>=3.1.0 || {
    echo "psycopg3 failed, trying psycopg2-binary..."
    pip install psycopg2-binary==2.9.9
}

echo "Installing remaining dependencies..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Setting Django settings module..."
export DJANGO_SETTINGS_MODULE=tuition.settings_staging
echo "DJANGO_SETTINGS_MODULE set to: $DJANGO_SETTINGS_MODULE"

echo "Checking database connection..."
python manage.py check --database default

echo "Running database migrations..."
python manage.py migrate --noinput --verbosity=2

echo "Checking migration status..."
python manage.py showmigrations

echo "Creating default admin user if it doesn't exist..."
python manage.py create_admin --first_name "Admin" --last_name "User" --email "admin@waprep.org" --password "Admin123!@#" || echo "Admin user already exists or error occurred"

echo "Verifying WSGI application..."
python -c "from tuition.wsgi import application; print('WSGI application loaded successfully')"

echo "Build completed successfully!"