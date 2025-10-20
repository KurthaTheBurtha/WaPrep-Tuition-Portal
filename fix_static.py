#!/usr/bin/env python
"""
Script to fix Django static files issues
"""
import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Set environment variables
os.environ.setdefault('SECRET_KEY', 'dev-secret-key-for-local-development-only')
os.environ.setdefault('DEBUG', 'True')
os.environ.setdefault('EMAIL_HOST_USER', 'dev@example.com')
os.environ.setdefault('EMAIL_HOST_PASSWORD', 'dev-password')
os.environ.setdefault('DEFAULT_FROM_EMAIL', 'dev@example.com')
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_dummy')
os.environ.setdefault('STRIPE_PUBLISHABLE_KEY', 'pk_test_dummy')
os.environ.setdefault('SUPERUSER_TOKEN', 'dev-token')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuition.settings')

# Setup Django
django.setup()

from django.core.management import execute_from_command_line

if __name__ == '__main__':
    print("Fixing Django static files...")
    
    # Run migrations first
    print("Running migrations...")
    execute_from_command_line(['manage.py', 'migrate'])
    
    # Collect static files
    print("Collecting static files...")
    execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])
    
    print("Static files fix complete!")
    print("You can now run: python manage.py runserver")

