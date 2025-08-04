#!/usr/bin/env python3
"""
Script to test staging deployment configuration locally
"""

import os
import sys
import subprocess
from pathlib import Path

def test_staging_deployment():
    """Test staging deployment configuration"""
    print("🧪 Testing staging deployment configuration...")
    
    # Set environment variables for staging
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tuition.settings_staging'
    os.environ['DEBUG'] = 'True'
    
    # Change to project directory
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)
    
    try:
        # Test 1: Django configuration
        print("1️⃣ Testing Django configuration...")
        result = subprocess.run([
            'python', 'manage.py', 'check'
        ], capture_output=True, text=True, check=True)
        print("✅ Django configuration is valid")
        
        # Test 2: Database connection
        print("\n2️⃣ Testing database connection...")
        result = subprocess.run([
            'python', 'manage.py', 'run_migrations'
        ], capture_output=True, text=True, check=True)
        print("✅ Database migrations completed")
        print(result.stdout)
        
        # Test 3: Static files collection
        print("\n3️⃣ Testing static files collection...")
        result = subprocess.run([
            'python', 'manage.py', 'collectstatic', '--noinput', '--dry-run'
        ], capture_output=True, text=True, check=True)
        print("✅ Static files collection works")
        
        # Test 4: WSGI application
        print("\n4️⃣ Testing WSGI application...")
        result = subprocess.run([
            'python', '-c', 'from tuition.wsgi import application; print("WSGI OK")'
        ], capture_output=True, text=True, check=True)
        print("✅ WSGI application loads successfully")
        
        print("\n🎉 All tests passed! Staging deployment should work correctly.")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Test failed: {e}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    test_staging_deployment() 