# settings.py

import os
from dotenv import load_dotenv
from pathlib import Path
from decouple import config

# BASE DIRECTORY
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

SECRET_KEY = os.getenv('SECRET_KEY')

# DEBUG SETTINGS
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '.railway.app',  # Railway domains
    '.render.com',   # Render domains
    '.onrender.com', # Render domains
    '.herokuapp.com', # Heroku domains
]

# APPLICATIONS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tuition',  # Your custom app
]

# MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tuition.audit_middleware.AuditMiddleware',
    'tuition.audit_middleware.SecurityMiddleware',
]

# URL CONFIGURATION
ROOT_URLCONF = 'tuition.urls'

# TEMPLATES
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGI APPLICATION
WSGI_APPLICATION = 'tuition.wsgi.application'

# DATABASE
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# PASSWORD VALIDATION
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# INTERNATIONALIZATION
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Los_Angeles'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# STATIC FILES
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Only add STATICFILES_DIRS if the static directory exists
import os
static_dir = BASE_DIR / "static"
if static_dir.exists():
    STATICFILES_DIRS = [static_dir]
else:
    STATICFILES_DIRS = []

# Add tuition app static files directory
tuition_static_dir = BASE_DIR / "tuition" / "static"
if tuition_static_dir.exists() and tuition_static_dir not in STATICFILES_DIRS:
    STATICFILES_DIRS.append(tuition_static_dir)

# DEFAULT PRIMARY KEY FIELD TYPE
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CUSTOM USER MODEL (if using one)
AUTH_USER_MODEL = 'tuition.User'  # Uncomment if using a custom user model

# EMAIL SETTINGS
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.office365.com'
EMAIL_PORT = 587  
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')

# LOGIN/LOGOUT REDIRECTS
LOGIN_URL = '/login/payer/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')

# MESSAGE STORAGE
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# LOGGING CONFIGURATION
# Create logs directory if it doesn't exist
import os
logs_dir = BASE_DIR / 'logs'
if not logs_dir.exists():
    try:
        logs_dir.mkdir(exist_ok=True)
    except (OSError, PermissionError):
        # If we can't create logs directory, use console-only logging
        pass

# Determine if we can use file logging
can_use_file_logging = logs_dir.exists() and os.access(logs_dir, os.W_OK)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'audit': {
            'format': '{asctime} | {levelname} | {user} | {ip} | {action} | {model} | {record_id} | {message}',
            'style': '{',
        },
        'security': {
            'format': '{asctime} | SECURITY | {levelname} | {user} | {ip} | {event_type} | {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'audit_filter': {
            '()': 'tuition.logging_filters.AuditFilter',
        },
        'security_filter': {
            '()': 'tuition.logging_filters.SecurityFilter',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'tuition.audit': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'tuition.security': {
            'handlers': ['console', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'tuition.monitoring': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Add file handlers only if we can write to logs directory
if can_use_file_logging:
    LOGGING['handlers'].update({
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': logs_dir / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'audit_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': logs_dir / 'audit.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 10,
            'formatter': 'audit',
            'filters': ['audit_filter'],
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': logs_dir / 'security.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 10,
            'formatter': 'security',
            'filters': ['security_filter'],
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': logs_dir / 'error.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    })
    
    # Update loggers to include file handlers
    LOGGING['loggers']['django']['handlers'].append('file')
    LOGGING['loggers']['django']['handlers'].append('error_file')
    LOGGING['loggers']['django.request']['handlers'].append('error_file')
    LOGGING['loggers']['django.security']['handlers'].append('security_file')
    LOGGING['loggers']['tuition.audit']['handlers'].append('audit_file')
    LOGGING['loggers']['tuition.security']['handlers'].append('security_file')
    LOGGING['loggers']['tuition.monitoring']['handlers'].append('file')
    LOGGING['root']['handlers'].append('file')

# AUDIT LOGGING SETTINGS
AUDIT_LOG_ENABLED = True
AUDIT_LOG_SENSITIVE_FIELDS = [
    'password', 'password_hash', 'stripe_customer_id', 'stripe_payment_method_id',
    'provider_token', 'routing_number', 'account_number', 'last4'
]
AUDIT_LOG_MAX_VALUE_LENGTH = 1000
AUDIT_LOG_RETENTION_DAYS = 365  # Keep audit logs for 1 year

# SECURITY SETTINGS
SECURITY_LOG_ENABLED = True
SECURITY_LOG_FAILED_LOGIN_ATTEMPTS = 5
SECURITY_LOG_SUSPICIOUS_ACTIVITY_THRESHOLD = 10
SECURITY_LOG_RATE_LIMIT_PER_MINUTE = 100

# MONITORING SETTINGS
MONITORING_ENABLED = True
MONITORING_HEALTH_CHECK_INTERVAL = 300  # 5 minutes
MONITORING_PERFORMANCE_THRESHOLD = 2.0  # seconds
MONITORING_DISK_USAGE_THRESHOLD = 80  # percentage
MONITORING_MEMORY_USAGE_THRESHOLD = 80  # percentage

# SECURITY SETTINGS FOR PRODUCTION
# HTTPS Settings
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False') == 'True'
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True') == 'True'
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'True') == 'True'

# Session Security
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = os.getenv('SESSION_EXPIRE_AT_BROWSER_CLOSE', 'False') == 'True'
SESSION_COOKIE_AGE = 900  # 15 minutes (15 * 60 seconds)
SESSION_SAVE_EVERY_REQUEST = True
SESSION_IDLE_TIMEOUT = 900  # 15 minutes in seconds

# CSRF Security
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False') == 'True'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://localhost:8000',
    'https://127.0.0.1:8000',
]

# Content Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Content Security Policy (commented out due to Python 3.8 compatibility issues)
# CSP_DEFAULT_SRC = ("'self'",)
# CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com")
# CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https://js.stripe.com")
# CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
# CSP_IMG_SRC = ("'self'", "data:", "https:")
# CSP_CONNECT_SRC = ("'self'", "https://api.stripe.com")

