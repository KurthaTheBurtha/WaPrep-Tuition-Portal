from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
import os

class Command(BaseCommand):
    help = 'Run migrations with detailed output and database connection check'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting migration process...'))
        
        # Check environment
        self.stdout.write(f"DJANGO_SETTINGS_MODULE: {os.environ.get('DJANGO_SETTINGS_MODULE', 'Not set')}")
        self.stdout.write(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'Not set')}")
        
        # Check database connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                self.stdout.write(f"Database connected: {version[0]}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Database connection failed: {e}"))
            return
        
        # Run migrations
        try:
            self.stdout.write("Running migrations...")
            call_command('migrate', verbosity=2, interactive=False)
            self.stdout.write(self.style.SUCCESS("Migrations completed successfully!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Migration failed: {e}"))
            return
        
        # Show migration status
        try:
            self.stdout.write("Migration status:")
            call_command('showmigrations')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Could not show migrations: {e}")) 