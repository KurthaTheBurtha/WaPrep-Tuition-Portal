from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
import os

class Command(BaseCommand):
    help = 'Set up production database with all tables and initial data'

    def handle(self, *args, **options):
        self.stdout.write('Setting up production database...')
        
        try:
            # Check database connection
            self.stdout.write('Checking database connection...')
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(self.style.SUCCESS('Database connection successful'))
            
            # Run migrations
            self.stdout.write('Running migrations...')
            call_command('migrate', verbosity=2)
            self.stdout.write(self.style.SUCCESS('Migrations completed'))
            
            # Show migration status
            self.stdout.write('Migration status:')
            call_command('showmigrations')
            
            # Create superuser if it doesn't exist
            self.stdout.write('Creating superuser...')
            call_command('create_mindy_superuser')
            
            self.stdout.write(self.style.SUCCESS('Production database setup completed successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error setting up database: {e}'))
            raise 