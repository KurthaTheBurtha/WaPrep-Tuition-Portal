from django.core.management.base import BaseCommand
from tuition.models import Student, PaymentBreakdown
from datetime import datetime, date, timedelta
import calendar


class Command(BaseCommand):
    help = 'Create test bills for Kurt and Klara Schimmel to demonstrate overdue ordering'

    def handle(self, *args, **options):
        # Get the Schimmel students
        try:
            kurt = Student.objects.get(first_name='Kurt', last_name='Schimmel')
            klara = Student.objects.get(first_name='Klara', last_name='Schimmel')
        except Student.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Kurt or Klara Schimmel not found. Please ensure they exist in the database.')
            )
            return

        # Clear existing bills for these students (to start fresh)
        PaymentBreakdown.objects.filter(student__in=[kurt, klara]).delete()
        self.stdout.write('Cleared existing bills for Kurt and Klara Schimmel')

        # Create test bills with various scenarios
        test_bills = []

        # Current date for reference
        today = date.today()
        
        # For Kurt Schimmel
        kurt_bills = [
            # Overdue bills (past late_date) - should appear at top
            {
                'student': kurt,
                'description': 'June Tuition - Overdue',
                'amount': 500.00,
                'due_date': date(2025, 6, 15),
                'date_incurred': date(2025, 6, 1),
                'late_date': date(2025, 6, 30),
                'is_paid': False
            },
            {
                'student': kurt,
                'description': 'May Lunch Program - Overdue',
                'amount': 100.00,
                'due_date': date(2025, 5, 20),
                'date_incurred': date(2025, 5, 1),
                'late_date': date(2025, 5, 31),
                'is_paid': False
            },
            {
                'student': kurt,
                'description': 'April Activity Fee - Overdue',
                'amount': 50.00,
                'due_date': date(2025, 4, 25),
                'date_incurred': date(2025, 4, 1),
                'late_date': date(2025, 4, 30),
                'is_paid': False
            },
            # Current month bills (not overdue yet)
            {
                'student': kurt,
                'description': 'July Tuition',
                'amount': 500.00,
                'due_date': date(2025, 7, 15),
                'date_incurred': date(2025, 7, 1),
                'late_date': date(2025, 7, 31),
                'is_paid': False
            },
            {
                'student': kurt,
                'description': 'July Lunch Program',
                'amount': 100.00,
                'due_date': date(2025, 7, 20),
                'date_incurred': date(2025, 7, 1),
                'late_date': date(2025, 7, 31),
                'is_paid': False
            },
            # Paid bills (should appear at bottom)
            {
                'student': kurt,
                'description': 'March Tuition - Paid',
                'amount': 500.00,
                'due_date': date(2025, 3, 15),
                'date_incurred': date(2025, 3, 1),
                'late_date': date(2025, 3, 31),
                'is_paid': True
            },
            {
                'student': kurt,
                'description': 'February Lunch Program - Paid',
                'amount': 100.00,
                'due_date': date(2025, 2, 20),
                'date_incurred': date(2025, 2, 1),
                'late_date': date(2025, 2, 28),
                'is_paid': True
            }
        ]

        # For Klara Schimmel
        klara_bills = [
            # Overdue bills (past late_date) - should appear at top
            {
                'student': klara,
                'description': 'June Tuition - Overdue',
                'amount': 500.00,
                'due_date': date(2025, 6, 10),
                'date_incurred': date(2025, 6, 1),
                'late_date': date(2025, 6, 30),
                'is_paid': False
            },
            {
                'student': klara,
                'description': 'May Activity Fee - Overdue',
                'amount': 50.00,
                'due_date': date(2025, 5, 25),
                'date_incurred': date(2025, 5, 1),
                'late_date': date(2025, 5, 31),
                'is_paid': False
            },
            # Current month bills (not overdue yet)
            {
                'student': klara,
                'description': 'July Tuition',
                'amount': 500.00,
                'due_date': date(2025, 7, 10),
                'date_incurred': date(2025, 7, 1),
                'late_date': date(2025, 7, 31),
                'is_paid': False
            },
            {
                'student': klara,
                'description': 'July Lunch Program',
                'amount': 100.00,
                'due_date': date(2025, 7, 25),
                'date_incurred': date(2025, 7, 1),
                'late_date': date(2025, 7, 31),
                'is_paid': False
            },
            # Paid bills (should appear at bottom)
            {
                'student': klara,
                'description': 'April Tuition - Paid',
                'amount': 500.00,
                'due_date': date(2025, 4, 15),
                'date_incurred': date(2025, 4, 1),
                'late_date': date(2025, 4, 30),
                'is_paid': True
            }
        ]

        # Create all bills
        all_bills = kurt_bills + klara_bills
        created_count = 0

        for bill_data in all_bills:
            bill = PaymentBreakdown.objects.create(**bill_data)
            created_count += 1
            self.stdout.write(
                f"Created: {bill.student.first_name} - {bill.description} "
                f"(${bill.amount}) - Due: {bill.due_date} - Late: {bill.late_date} "
                f"- {'PAID' if bill.is_paid else 'UNPAID'}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} test bills for Kurt and Klara Schimmel'
            )
        )
        
        # Show summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write('TEST BILLS SUMMARY')
        self.stdout.write('='*60)
        
        for student in [kurt, klara]:
            self.stdout.write(f'\n{student.first_name} {student.last_name}:')
            
            # Overdue bills
            overdue_bills = student.payment_breakdowns.filter(is_paid=False, late_date__lt=today)
            if overdue_bills.exists():
                self.stdout.write('  OVERDUE BILLS:')
                for bill in overdue_bills:
                    days_overdue = (today - bill.late_date).days
                    self.stdout.write(f'    - {bill.description} (${bill.amount}) - {days_overdue} days overdue')
            
            # Current unpaid bills
            current_bills = student.payment_breakdowns.filter(is_paid=False, late_date__gte=today)
            if current_bills.exists():
                self.stdout.write('  CURRENT UNPAID BILLS:')
                for bill in current_bills:
                    self.stdout.write(f'    - {bill.description} (${bill.amount}) - Due: {bill.due_date}')
            
            # Paid bills
            paid_bills = student.payment_breakdowns.filter(is_paid=True)
            if paid_bills.exists():
                self.stdout.write('  PAID BILLS:')
                for bill in paid_bills:
                    self.stdout.write(f'    - {bill.description} (${bill.amount})')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write('DEMONSTRATION NOTES:')
        self.stdout.write('='*60)
        self.stdout.write('1. Overdue bills will appear at the top (red "Overdue" badges)')
        self.stdout.write('2. Current unpaid bills will appear in the middle (yellow "Unpaid" badges)')
        self.stdout.write('3. Paid bills will appear at the bottom (green "Paid" badges)')
        self.stdout.write('4. Overdue bills are sorted by how many days they are overdue')
        self.stdout.write('5. Bills are only considered overdue after their late_date (not due_date)')
        self.stdout.write('\nTo view: Go to Admin Dashboard > Manage Billing > Click on Kurt or Klara') 