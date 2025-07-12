from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

class Command(BaseCommand):
    help = 'Perform system health checks and backup monitoring'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-alerts',
            action='store_true',
            help='Send email alerts for failures',
        )
        parser.add_argument(
            '--check-backups',
            action='store_true',
            help='Check backup status and recent backups',
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting WAPrep Tuition Portal health checks...")
        
        checks = [
            self.check_database_connection,
            self.check_database_size,
            self.check_stripe_connection,
            self.check_static_files,
            self.check_environment_variables,
        ]
        
        if options['check_backups']:
            checks.append(self.check_backup_status)
        
        failed_checks = []
        
        for check in checks:
            try:
                result = check()
                if result:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ {check.__name__} passed")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"✗ {check.__name__} failed")
                    )
                    failed_checks.append(check.__name__)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ {check.__name__} failed: {e}")
                )
                failed_checks.append(check.__name__)
        
        # Summary
        if failed_checks:
            self.stdout.write(
                self.style.WARNING(f"\n{len(failed_checks)} checks failed:")
            )
            for check in failed_checks:
                self.stdout.write(f"  - {check}")
            
            if options['send_alerts']:
                self.send_alert(failed_checks)
        else:
            self.stdout.write(
                self.style.SUCCESS("\nAll health checks passed!")
            )

    def check_database_connection(self):
        """Check database connectivity"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            self.stdout.write(f"Database connection failed: {e}")
            return False

    def check_database_size(self):
        """Check database size and report"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
                size = cursor.fetchone()[0]
                self.stdout.write(f"Database size: {size}")
                
                # Check if database is getting too large
                cursor.execute("SELECT pg_database_size(current_database())")
                size_bytes = cursor.fetchone()[0]
                size_mb = size_bytes / (1024 * 1024)
                
                if size_mb > 1000:  # Warning if over 1GB
                    self.stdout.write(
                        self.style.WARNING(f"Database is large: {size_mb:.1f} MB")
                    )
                
                return True
        except Exception as e:
            self.stdout.write(f"Database size check failed: {e}")
            return False

    def check_stripe_connection(self):
        """Check Stripe API connectivity"""
        try:
            import stripe
            stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
            
            if not stripe.api_key:
                self.stdout.write("Stripe API key not configured")
                return False
            
            # Test Stripe connection
            stripe.Account.retrieve()
            return True
        except Exception as e:
            self.stdout.write(f"Stripe connection failed: {e}")
            return False

    def check_static_files(self):
        """Check if static files are accessible"""
        try:
            static_root = getattr(settings, 'STATIC_ROOT', None)
            if static_root and os.path.exists(static_root):
                # Check if static files directory has content
                files = os.listdir(static_root)
                if files:
                    self.stdout.write(f"Static files found: {len(files)} files")
                    return True
                else:
                    self.stdout.write("Static files directory is empty")
                    return False
            else:
                self.stdout.write("Static files directory not found")
                return False
        except Exception as e:
            self.stdout.write(f"Static files check failed: {e}")
            return False

    def check_environment_variables(self):
        """Check critical environment variables"""
        critical_vars = [
            'SECRET_KEY',
            'DATABASE_URL',
            'STRIPE_SECRET_KEY',
            'STRIPE_PUBLISHABLE_KEY',
        ]
        
        missing_vars = []
        for var in critical_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.stdout.write(f"Missing environment variables: {', '.join(missing_vars)}")
            return False
        
        return True

    def check_backup_status(self):
        """Check if recent backups exist and are valid"""
        try:
            backup_dir = "/backups/daily/database"
            s3_bucket = os.getenv('S3_BACKUP_BUCKET')
            
            # Check local backups
            if os.path.exists(backup_dir):
                backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.sql.gz')]
                if backup_files:
                    # Get most recent backup
                    latest_backup = max(backup_files, key=lambda x: os.path.getctime(os.path.join(backup_dir, x)))
                    backup_time = datetime.fromtimestamp(os.path.getctime(os.path.join(backup_dir, latest_backup)))
                    
                    # Check if backup is recent (within 24 hours)
                    if datetime.now() - backup_time < timedelta(hours=24):
                        self.stdout.write(f"Recent local backup found: {latest_backup}")
                        return True
                    else:
                        self.stdout.write(f"Local backup is old: {latest_backup} from {backup_time}")
                        return False
                else:
                    self.stdout.write("No local backup files found")
                    return False
            else:
                self.stdout.write("Local backup directory not found")
            
            # Check S3 backups if configured
            if s3_bucket:
                try:
                    s3_client = boto3.client('s3')
                    response = s3_client.list_objects_v2(
                        Bucket=s3_bucket,
                        Prefix='database/',
                        MaxKeys=1
                    )
                    
                    if 'Contents' in response:
                        latest_s3_backup = response['Contents'][0]['Key']
                        backup_time = response['Contents'][0]['LastModified']
                        
                        if datetime.now(backup_time.tzinfo) - backup_time < timedelta(hours=24):
                            self.stdout.write(f"Recent S3 backup found: {latest_s3_backup}")
                            return True
                        else:
                            self.stdout.write(f"S3 backup is old: {latest_s3_backup} from {backup_time}")
                            return False
                    else:
                        self.stdout.write("No S3 backup files found")
                        return False
                        
                except ClientError as e:
                    self.stdout.write(f"S3 backup check failed: {e}")
                    return False
            
            return False
            
        except Exception as e:
            self.stdout.write(f"Backup status check failed: {e}")
            return False

    def send_alert(self, failed_checks):
        """Send email alert for failed health checks"""
        try:
            email_host = getattr(settings, 'EMAIL_HOST', None)
            email_port = getattr(settings, 'EMAIL_PORT', None)
            email_user = getattr(settings, 'EMAIL_HOST_USER', None)
            email_password = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
            
            if not all([email_host, email_port, email_user, email_password]):
                self.stdout.write("Email settings not configured, skipping alert")
                return
            
            # Get admin email from environment or settings
            admin_email = os.getenv('ADMIN_EMAIL', 'admin@waprep.com')
            
            subject = f"WAPrep Health Check Alert - {len(failed_checks)} failures"
            message = f"""
WAPrep Tuition Portal Health Check Alert

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Failed Checks: {', '.join(failed_checks)}

Please investigate the following issues:
{chr(10).join([f"- {check}" for check in failed_checks])}

This is an automated alert from the WAPrep Tuition Portal health monitoring system.
            """
            
            msg = MIMEText(message)
            msg['Subject'] = subject
            msg['From'] = email_user
            msg['To'] = admin_email
            
            with smtplib.SMTP(email_host, email_port) as server:
                server.starttls()
                server.login(email_user, email_password)
                server.send_message(msg)
            
            self.stdout.write(f"Alert sent to {admin_email}")
            
        except Exception as e:
            self.stdout.write(f"Failed to send alert: {e}") 