from django.core.management.base import BaseCommand
from tuition.models import User
from django.db import models


class Command(BaseCommand):
    help = 'Delete users named "Dad Bob", "Dad Schimmel", and payers named "Test Payer"'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        # Find users to delete
        users_to_delete = User.objects.filter(
            models.Q(first_name='Dad', last_name='Bob') |
            models.Q(first_name='Dad', last_name='Schimmel') |
            models.Q(first_name='Test', last_name='Payer', user_type='payer') |
            models.Q(first_name='0')
        )
        
        count = users_to_delete.count()
        
        if count == 0:
            self.stdout.write(
                self.style.WARNING('No matching users found to delete.')
            )
            return
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would delete {count} user(s):')
            )
            for user in users_to_delete:
                self.stdout.write(f'  - {user.first_name} {user.last_name} (ID: {user.id}, Email: {user.email}, Type: {user.user_type})')
            return
        
        # Confirm deletion
        self.stdout.write(
            self.style.WARNING(f'Found {count} user(s) to delete:')
        )
        for user in users_to_delete:
            self.stdout.write(f'  - {user.first_name} {user.last_name} (ID: {user.id}, Email: {user.email}, Type: {user.user_type})')
        
        confirm = input('\nAre you sure you want to delete these users? (yes/no): ')
        
        if confirm.lower() in ['yes', 'y']:
            deleted_count = users_to_delete.delete()[0]
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {deleted_count} user(s)')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Deletion cancelled.')
            ) 