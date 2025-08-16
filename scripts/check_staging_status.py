#!/usr/bin/env python3
"""
Script to check staging environment status
"""

import os
import sys
import subprocess
from pathlib import Path

def check_staging_status():
    """Check staging environment status"""
    print("🔍 Checking staging environment status...")
    
    # Set environment variables for staging
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tuition.settings_staging'
    os.environ['DEBUG'] = 'True'
    
    # Change to project directory
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)
    
    try:
        # Check Django configuration
        print("📋 Django Configuration:")
        result = subprocess.run([
            'python', 'manage.py', 'check'
        ], capture_output=True, text=True, check=True)
        print(result.stdout)
        
        # Check database connection
        print("\n🗄️ Database Connection:")
        result = subprocess.run([
            'python', 'manage.py', 'dbshell', '-c', 'SELECT version();'
        ], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Database connection successful")
            print(result.stdout)
        else:
            print("❌ Database connection failed")
            print(result.stderr)
        
        # Check migration status
        print("\n📊 Migration Status:")
        result = subprocess.run([
            'python', 'manage.py', 'showmigrations'
        ], capture_output=True, text=True, check=True)
        print(result.stdout)
        
        # Check if tables exist
        print("\n📋 Checking if tables exist:")
        result = subprocess.run([
            'python', 'manage.py', 'dbshell', '-c', "\\dt"
        ], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Database tables:")
            print(result.stdout)
        else:
            print("❌ Could not check tables")
            print(result.stderr)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Check failed: {e}")
        print(f"Error output: {e.stderr}")
    except subprocess.TimeoutExpired:
        print("❌ Database connection timed out")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == '__main__':
    check_staging_status() 