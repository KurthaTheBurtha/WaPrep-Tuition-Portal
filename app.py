"""
WSGI application entry point for WaPrep Tuition Portal
This file serves as a fallback for deployment platforms that expect 'app:app'
"""

import os
from django.core.wsgi import get_wsgi_application

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuition.settings_production')

# Get the WSGI application
app = get_wsgi_application()

# Export the application
application = app