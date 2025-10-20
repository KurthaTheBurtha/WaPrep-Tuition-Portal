#!/bin/bash
# Django Development Server Startup Script

echo "Starting WaPrep Tuition Portal Development Server..."

# Kill any existing Django processes on port 8000
echo "Checking for existing Django processes..."
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "Killing existing Django processes on port 8000..."
    lsof -ti:8000 | xargs kill -9
    sleep 2
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Set required environment variables
echo "Setting environment variables..."
export SECRET_KEY="dev-secret-key-for-local-development-only"
export DEBUG="True"
export EMAIL_HOST_USER="dev@example.com"
export EMAIL_HOST_PASSWORD="dev-password"
export DEFAULT_FROM_EMAIL="dev@example.com"
export STRIPE_SECRET_KEY="sk_test_dummy"
export STRIPE_PUBLISHABLE_KEY="pk_test_dummy"
export SUPERUSER_TOKEN="dev-token"

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Django development server
echo "Starting Django development server on http://localhost:8000..."
echo "Press Ctrl+C to stop the server"
python manage.py runserver
