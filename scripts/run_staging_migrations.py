#!/usr/bin/env python3
"""
Script to run migrations on the staging environment
"""

import os
import sys
import subprocess
from pathlib import Path

def run_staging_migrations():
    """Run migrations on staging environment"""
    print("🚀 Running migrations on staging environment...")
    
    # Set environment variables for staging
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tuition.settings_staging'
    os.environ['DEBUG'] = 'True'
    
    # Change to project directory
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)
    
    try:
        # Run migrations
        print("Running migrations...")
        result = subprocess.run([
            'python', 'manage.py', 'run_migrations'
        ], capture_output=True, text=True, check=True)
        
        print("✅ Migrations completed successfully!")
        print(result.stdout)
        
        # Show migration status
        print("\n📊 Migration Status:")
        result = subprocess.run([
            'python', 'manage.py', 'showmigrations'
        ], capture_output=True, text=True, check=True)
        
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_staging_migrations() 