from django.core.management.base import BaseCommand
from tuition.models import Student


class Command(BaseCommand):
    help = 'Delete all students named "Test Student"'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        # Find all students named "Test Student"
        test_students = Student.objects.filter(
            first_name='Test',
            last_name='Student'
        )
        
        count = test_students.count()
        
        if count == 0:
            self.stdout.write(
                self.style.WARNING('No students named "Test Student" found.')
            )
            return
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would delete {count} student(s) named "Test Student":')
            )
            for student in test_students:
                self.stdout.write(f'  - {student.first_name} {student.last_name} (ID: {student.student_id})')
            return
        
        # Confirm deletion
        self.stdout.write(
            self.style.WARNING(f'Found {count} student(s) named "Test Student"')
        )
        
        for student in test_students:
            self.stdout.write(f'  - {student.first_name} {student.last_name} (ID: {student.student_id})')
        
        confirm = input('\nAre you sure you want to delete these students? (yes/no): ')
        
        if confirm.lower() in ['yes', 'y']:
            # Delete the students
            deleted_count = test_students.delete()[0]
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {deleted_count} student(s) named "Test Student"')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Deletion cancelled.')
            ) 