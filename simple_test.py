#!/usr/bin/env python3
"""
Simple test script to identify 500 errors.
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuition.settings')
django.setup()

def test_basic_imports():
    """Test basic imports to identify any missing dependencies."""
    print("Testing basic imports...")
    
    try:
        from tuition.models import User, Student, Payment, AccountRequest
        print("✅ Models imported successfully")
    except Exception as e:
        print(f"❌ Model import error: {e}")
    
    try:
        from tuition.forms import AccountRequestForm
        print("✅ Forms imported successfully")
    except Exception as e:
        print(f"❌ Form import error: {e}")
    
    try:
        from tuition.views import request_account_view, forgot_password
        print("✅ Views imported successfully")
    except Exception as e:
        print(f"❌ View import error: {e}")
    
    try:
        from tuition.utils import validate_password, generate_strong_password
        print("✅ Utils imported successfully")
    except Exception as e:
        print(f"❌ Utils import error: {e}")

def test_settings():
    """Test settings configuration."""
    print("\nTesting settings...")
    
    try:
        print(f"✅ DEBUG: {settings.DEBUG}")
        print(f"✅ SECRET_KEY: {settings.SECRET_KEY[:10]}..." if settings.SECRET_KEY else "❌ SECRET_KEY: None")
        print(f"✅ EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        print(f"✅ DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        print(f"✅ STRIPE_SECRET_KEY: {settings.STRIPE_SECRET_KEY[:10]}..." if settings.STRIPE_SECRET_KEY else "❌ STRIPE_SECRET_KEY: None")
    except Exception as e:
        print(f"❌ Settings error: {e}")

def test_database():
    """Test database connection."""
    print("\nTesting database...")
    
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    print("🔍 Simple Test for WAPrep Tuition Application...")
    print("=" * 60)
    
    test_basic_imports()
    test_settings()
    test_database()
    
    print("\n" + "=" * 60)
    print("Simple testing completed.") 