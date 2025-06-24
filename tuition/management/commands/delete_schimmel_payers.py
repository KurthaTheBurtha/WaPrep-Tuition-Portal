from django.core.management.base import BaseCommand
from tuition.models import User


class Command(BaseCommand):
    help = 'Delete all payers named "Dad Schimmel" and "Mama Schimmel"'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        # Find all payers named Dad Schimmel or Mama Schimmel
        payers = User.objects.filter(
            user_type='payer',
            first_name__in=['Dad', 'Mama'],
            last_name='Schimmel'
        )
        
        count = payers.count()
        
        if count == 0:
            self.stdout.write(
                self.style.WARNING('No payers named "Dad Schimmel" or "Mama Schimmel" found.')
            )
            return
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would delete {count} payer(s) named Dad/Mama Schimmel:')
            )
            for payer in payers:
                self.stdout.write(f'  - {payer.first_name} {payer.last_name} (ID: {payer.id}, Email: {payer.email})')
            return
        
        # Confirm deletion
        self.stdout.write(
            self.style.WARNING(f'Found {count} payer(s) named Dad/Mama Schimmel:')
        )
        for payer in payers:
            self.stdout.write(f'  - {payer.first_name} {payer.last_name} (ID: {payer.id}, Email: {payer.email})')
        
        confirm = input('\nAre you sure you want to delete these payers? (yes/no): ')
        
        if confirm.lower() in ['yes', 'y']:
            deleted_count = payers.delete()[0]
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {deleted_count} payer(s) named Dad/Mama Schimmel')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Deletion cancelled.')
            ) 