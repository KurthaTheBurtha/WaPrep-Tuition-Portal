#!/usr/bin/env python3
"""
WAPrep Tuition Portal - Emergency Recovery Script
This script handles emergency recovery of database and files from backups
"""

import os
import sys
import subprocess
import argparse
import django
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuition.settings_production')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection
from tuition.models import User, Student, Payment, PaymentBreakdown

class RecoveryManager:
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        self.s3_bucket = os.getenv('S3_BACKUP_BUCKET', 'your-waprep-backup-bucket')
        self.backup_dir = '/backups'
        
    def log(self, message, level='INFO'):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")
    
    def check_prerequisites(self):
        """Check if all prerequisites are met for recovery"""
        self.log("Checking prerequisites...")
        
        if not self.db_url:
            self.log("DATABASE_URL not set", "ERROR")
            return False
            
        if not os.path.exists(self.backup_dir):
            self.log(f"Backup directory {self.backup_dir} not found", "ERROR")
            return False
            
        self.log("Prerequisites check passed")
        return True
    
    def list_available_backups(self):
        """List available backups from local storage and S3"""
        self.log("Listing available backups...")
        
        # Local backups
        local_backups = []
        if os.path.exists(f"{self.backup_dir}/daily/database"):
            for file in os.listdir(f"{self.backup_dir}/daily/database"):
                if file.endswith('.sql.gz'):
                    local_backups.append(f"local:{file}")
        
        # S3 backups (if configured)
        s3_backups = []
        try:
            s3_client = boto3.client('s3')
            response = s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix='database/'
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('.sql.gz'):
                        s3_backups.append(f"s3:{obj['Key']}")
                        
        except Exception as e:
            self.log(f"Could not list S3 backups: {e}", "WARNING")
        
        return local_backups, s3_backups
    
    def download_backup_from_s3(self, s3_key, local_path):
        """Download backup from S3"""
        try:
            s3_client = boto3.client('s3')
            s3_client.download_file(self.s3_bucket, s3_key, local_path)
            self.log(f"Downloaded {s3_key} to {local_path}")
            return True
        except ClientError as e:
            self.log(f"Failed to download from S3: {e}", "ERROR")
            return False
    
    def restore_database(self, backup_file):
        """Restore database from backup file"""
        self.log(f"Starting database restoration from {backup_file}")
        
        # Stop application (platform-specific)
        self.stop_application()
        
        try:
            # Restore database
            if backup_file.endswith('.sql.gz'):
                # Decompress and restore
                subprocess.run(['gunzip', '-c', backup_file], 
                             stdout=subprocess.PIPE, check=True)
                sql_file = backup_file[:-3]  # Remove .gz
                
                # Restore using psql
                subprocess.run(['psql', self.db_url, '-f', sql_file], check=True)
                
                # Clean up temporary file
                os.remove(sql_file)
            else:
                # Direct restore
                subprocess.run(['psql', self.db_url, '-f', backup_file], check=True)
            
            # Run migrations
            self.log("Running Django migrations...")
            execute_from_command_line(['manage.py', 'migrate'])
            
            # Verify data integrity
            self.verify_data_integrity()
            
            self.log("Database restoration completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Database restoration failed: {e}", "ERROR")
            return False
        finally:
            # Start application
            self.start_application()
    
    def restore_files(self, backup_file):
        """Restore files from backup"""
        self.log(f"Starting file restoration from {backup_file}")
        
        try:
            # Extract files
            subprocess.run(['tar', '-xzf', backup_file, '-C', '/app'], check=True)
            self.log("File restoration completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"File restoration failed: {e}", "ERROR")
            return False
    
    def verify_data_integrity(self):
        """Verify critical data after recovery"""
        self.log("Verifying data integrity...")
        
        try:
            # Check user count
            user_count = User.objects.count()
            self.log(f"Users recovered: {user_count}")
            
            # Check student count
            student_count = Student.objects.count()
            self.log(f"Students recovered: {student_count}")
            
            # Check payment count
            payment_count = Payment.objects.count()
            self.log(f"Payments recovered: {payment_count}")
            
            # Check payment breakdown count
            breakdown_count = PaymentBreakdown.objects.count()
            self.log(f"Payment breakdowns recovered: {breakdown_count}")
            
            # Check database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                self.log(f"Database version: {version}")
            
            self.log("Data integrity verification completed")
            return True
            
        except Exception as e:
            self.log(f"Data integrity check failed: {e}", "ERROR")
            return False
    
    def stop_application(self):
        """Stop the application (platform-specific)"""
        self.log("Stopping application...")
        
        # This is platform-specific - adjust for your deployment
        # For Railway/Render/Heroku, you might need to use their CLI
        # or the application will be stopped by the platform
        
        # Example for Railway:
        # subprocess.run(['railway', 'service', 'stop'], check=True)
        
        # For now, we'll just log it
        self.log("Application stop command would be executed here")
    
    def start_application(self):
        """Start the application (platform-specific)"""
        self.log("Starting application...")
        
        # This is platform-specific - adjust for your deployment
        # Example for Railway:
        # subprocess.run(['railway', 'service', 'start'], check=True)
        
        # For now, we'll just log it
        self.log("Application start command would be executed here")
    
    def full_recovery(self, backup_source, backup_type='database'):
        """Perform full recovery procedure"""
        self.log(f"Starting full recovery from {backup_source}")
        
        if not self.check_prerequisites():
            return False
        
        # Determine backup file
        if backup_source.startswith('s3:'):
            # Download from S3
            s3_key = backup_source[3:]  # Remove 's3:' prefix
            local_path = f"/tmp/{os.path.basename(s3_key)}"
            
            if not self.download_backup_from_s3(s3_key, local_path):
                return False
                
            backup_file = local_path
        else:
            # Local file
            backup_file = f"{self.backup_dir}/daily/{backup_type}/{backup_source[6:]}"  # Remove 'local:' prefix
        
        # Perform recovery
        if backup_type == 'database':
            success = self.restore_database(backup_file)
        elif backup_type == 'files':
            success = self.restore_files(backup_file)
        else:
            self.log(f"Unknown backup type: {backup_type}", "ERROR")
            return False
        
        # Cleanup temporary files
        if backup_source.startswith('s3:') and os.path.exists(backup_file):
            os.remove(backup_file)
        
        return success

def main():
    parser = argparse.ArgumentParser(description='WAPrep Tuition Portal Recovery Tool')
    parser.add_argument('--list', action='store_true', help='List available backups')
    parser.add_argument('--recover', type=str, help='Recover from specific backup')
    parser.add_argument('--type', choices=['database', 'files'], default='database', 
                       help='Type of backup to recover')
    parser.add_argument('--verify', action='store_true', help='Verify data integrity only')
    
    args = parser.parse_args()
    
    recovery = RecoveryManager()
    
    if args.list:
        local_backups, s3_backups = recovery.list_available_backups()
        print("\nLocal backups:")
        for backup in local_backups:
            print(f"  {backup}")
        print("\nS3 backups:")
        for backup in s3_backups:
            print(f"  {backup}")
    
    elif args.verify:
        recovery.verify_data_integrity()
    
    elif args.recover:
        success = recovery.full_recovery(args.recover, args.type)
        if success:
            print("Recovery completed successfully!")
        else:
            print("Recovery failed!")
            sys.exit(1)
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main() 