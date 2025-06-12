from django.core.management.base import BaseCommand
from tuition.models import Student, PaymentBreakdown
from datetime import date, timedelta
from decimal import Decimal

class Command(BaseCommand):
    help = 'Creates dummy payment breakdown items for students'

    def handle(self, *args, **kwargs):
        # Get all students
        students = Student.objects.all()
        
        # Common payment items
        payment_items = [
            {
                'description': '2024-2025 Annual Tuition',
                'amount': Decimal('15000.00'),
                'due_date': date(2024, 8, 1)
            },
            {
                'description': 'Registration Fee',
                'amount': Decimal('250.00'),
                'due_date': date(2024, 7, 15)
            },
            {
                'description': 'Technology Fee',
                'amount': Decimal('200.00'),
                'due_date': date(2024, 8, 1)
            },
            {
                'description': 'Lunch Program - Fall Semester',
                'amount': Decimal('750.00'),
                'due_date': date(2024, 8, 1)
            },
            {
                'description': 'Lunch Program - Spring Semester',
                'amount': Decimal('750.00'),
                'due_date': date(2024, 1, 15)
            },
            {
                'description': 'Athletic Fee',
                'amount': Decimal('150.00'),
                'due_date': date(2024, 8, 1)
            },
            {
                'description': 'Activity Fee',
                'amount': Decimal('100.00'),
                'due_date': date(2024, 8, 1)
            },
            {
                'description': 'Yearbook',
                'amount': Decimal('75.00'),
                'due_date': date(2024, 10, 1)
            }
        ]

        # Create payment breakdown items for each student
        for student in students:
            self.stdout.write(f'Creating payment items for {student.first_name} {student.last_name}...')
            
            for item in payment_items:
                PaymentBreakdown.objects.create(
                    student=student,
                    description=item['description'],
                    amount=item['amount'],
                    due_date=item['due_date'],
                    is_paid=False
                )
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created payment items for {student.first_name} {student.last_name}')) 