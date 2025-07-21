from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, date, timedelta
import calendar
from decimal import Decimal
from tuition.models import Student, PaymentBreakdown

class Command(BaseCommand):
    help = 'Add current month and overdue bills for Kurt Schimmel'

    def handle(self, *args, **options):
        # Find Kurt Schimmel
        try:
            kurt = Student.objects.get(first_name='Kurt', last_name='Schimmel')
        except Student.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Kurt Schimmel not found. Please run add_schimmel_payment_test_data first.')
            )
            return

        # Clear existing unpaid bills for Kurt
        PaymentBreakdown.objects.filter(student=kurt, is_paid=False).delete()
        
        # Get current date info
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        # Calculate dates
        today = current_date.date()
        last_day_of_month = calendar.monthrange(current_year, current_month)[1]
        end_of_month = date(current_year, current_month, last_day_of_month)
        
        self.stdout.write(f"Current date: {today}")
        self.stdout.write(f"End of month: {end_of_month}")
        
        # Overdue bills (past late_date) - should appear in overdue accordion
        overdue_bills = [
            {
                'student': kurt,
                'description': 'January Tuition - Overdue',
                'amount': 500.00,
                'due_date': date(current_year, 1, 15),
                'date_incurred': date(current_year, 1, 1),
                'late_date': date(current_year, 1, 31),
                'is_paid': False
            },
            {
                'student': kurt,
                'description': 'February Lunch Program - Overdue',
                'amount': 120.00,
                'due_date': date(current_year, 2, 1),
                'date_incurred': date(current_year, 2, 1),
                'late_date': date(current_year, 2, 15),
                'is_paid': False
            },
            {
                'student': kurt,
                'description': 'March Tech Fee - Overdue',
                'amount': 75.00,
                'due_date': date(current_year, 3, 10),
                'date_incurred': date(current_year, 3, 1),
                'late_date': date(current_year, 3, 25),
                'is_paid': False
            }
        ]
        
        # Current month bills (due by end of current month) - should appear in current month accordion
        current_month_bills = [
            {
                'student': kurt,
                'description': f'{current_date.strftime("%B")} Tuition',
                'amount': 500.00,
                'due_date': end_of_month,
                'date_incurred': date(current_year, current_month, 1),
                'late_date': end_of_month + timedelta(days=15),
                'is_paid': False
            },
            {
                'student': kurt,
                'description': f'{current_date.strftime("%B")} Lunch Program',
                'amount': 120.00,
                'due_date': end_of_month,
                'date_incurred': date(current_year, current_month, 1),
                'late_date': end_of_month + timedelta(days=15),
                'is_paid': False
            },
            {
                'student': kurt,
                'description': f'{current_date.strftime("%B")} Tech Fee',
                'amount': 75.00,
                'due_date': end_of_month,
                'date_incurred': date(current_year, current_month, 1),
                'late_date': end_of_month + timedelta(days=15),
                'is_paid': False
            }
        ]
        
        # Create overdue bills
        for bill_data in overdue_bills:
            PaymentBreakdown.objects.create(**bill_data)
            self.stdout.write(f"Created overdue bill: {bill_data['description']} - ${bill_data['amount']}")
        
        # Create current month bills
        for bill_data in current_month_bills:
            PaymentBreakdown.objects.create(**bill_data)
            self.stdout.write(f"Created current month bill: {bill_data['description']} - ${bill_data['amount']}")
        
        # Calculate totals
        overdue_total = sum(bill['amount'] for bill in overdue_bills)
        current_month_total = sum(bill['amount'] for bill in current_month_bills)
        total_amount = overdue_total + current_month_total
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Successfully added bills for Kurt Schimmel:"))
        self.stdout.write(f"   Overdue bills: ${overdue_total:.2f}")
        self.stdout.write(f"   Current month bills: ${current_month_total:.2f}")
        self.stdout.write(f"   Total amount due: ${total_amount:.2f}")
        
        self.stdout.write(self.style.SUCCESS(f"\n🎯 Payment Priority Order:"))
        self.stdout.write(f"   1. Overdue bills (${overdue_total:.2f})")
        self.stdout.write(f"   2. Current month bills (${current_month_total:.2f})")
        
        self.stdout.write(self.style.SUCCESS(f"\n💡 Test Scenarios:"))
        self.stdout.write(f"   - Pay ${overdue_total:.2f} to cover all overdue bills")
        self.stdout.write(f"   - Pay ${current_month_total:.2f} to cover all current month bills")
        self.stdout.write(f"   - Pay ${total_amount:.2f} to cover everything")
        self.stdout.write(f"   - Pay partial amounts to test priority allocation") 