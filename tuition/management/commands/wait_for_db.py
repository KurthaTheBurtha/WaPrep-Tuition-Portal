from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError
import time

class Command(BaseCommand):
    help = 'Wait for database to be ready'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Timeout in seconds (default: 30)'
        )

    def handle(self, *args, **options):
        self.stdout.write('Waiting for database...')
        timeout = options['timeout']
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                db_conn = connections['default']
                db_conn.cursor()
                self.stdout.write(
                    self.style.SUCCESS('Database is ready!')
                )
                return
            except OperationalError:
                self.stdout.write('Database unavailable, waiting 1 second...')
                time.sleep(1)
        
        self.stdout.write(
            self.style.ERROR(f'Database not ready after {timeout} seconds')
        )
        raise Exception('Database connection timeout') 