#!/usr/bin/env python3
"""
Script to manually fix the staging database by running migrations
"""

import os
import sys
import subprocess
from pathlib import Path

def fix_staging_database():
    """Fix staging database by running migrations"""
    print("🔧 Fixing staging database...")
    
    # Set environment variables for staging
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tuition.settings_staging'
    os.environ['DEBUG'] = 'True'
    
    # Change to project directory
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)
    
    try:
        # Check current migration status
        print("📊 Current migration status:")
        result = subprocess.run([
            'python', 'manage.py', 'showmigrations'
        ], capture_output=True, text=True, check=True)
        print(result.stdout)
        
        # Run migrations
        print("\n🗄️ Running migrations...")
        result = subprocess.run([
            'python', 'manage.py', 'run_migrations'
        ], capture_output=True, text=True, check=True)
        print("✅ Migrations completed successfully!")
        print(result.stdout)
        
        # Show final migration status
        print("\n📊 Final migration status:")
        result = subprocess.run([
            'python', 'manage.py', 'showmigrations'
        ], capture_output=True, text=True, check=True)
        print(result.stdout)
        
        print("\n🎉 Staging database has been fixed!")
        print("The application should now work correctly.")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Database fix failed: {e}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    fix_staging_database() 