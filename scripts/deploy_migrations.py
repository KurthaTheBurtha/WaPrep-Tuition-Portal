#!/usr/bin/env python3
"""
Deployment script for running migrations on Render
This script is designed to be run on the Render environment
"""

import os
import sys
import subprocess
from pathlib import Path

def deploy_migrations():
    """Run migrations on Render environment"""
    print("🚀 Deploying migrations on Render...")
    
    # Set environment variables for staging
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tuition.settings_staging'
    os.environ['DEBUG'] = 'True'
    
    # Change to project directory
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)
    
    try:
        # Wait for database
        print("⏳ Waiting for database...")
        subprocess.run([
            'python', 'manage.py', 'wait_for_db', '--timeout=60'
        ], check=True)
        
        # Run migrations
        print("🗄️ Running migrations...")
        subprocess.run([
            'python', 'manage.py', 'run_migrations'
        ], check=True)
        
        # Collect static files
        print("📁 Collecting static files...")
        subprocess.run([
            'python', 'manage.py', 'collectstatic', '--noinput'
        ], check=True)
        
        print("✅ Deployment completed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    deploy_migrations() 