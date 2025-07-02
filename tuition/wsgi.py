import os
from django.core.wsgi import get_wsgi_application

# Use production settings by default for deployment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuition.settings_production')
application = get_wsgi_application()