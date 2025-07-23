from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, date, timedelta
import calendar
from decimal import Decimal
from tuition.models import Student, PaymentBreakdown

class Command(BaseCommand):
    help = 'Add overdue and upcoming bills for Klara Schimmel'

    def handle(self, *args, **options):
        # Find Klara Schimmel
        try:
            klara = Student.objects.get(first_name='Klara', last_name='Schimmel')
        except Student.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Klara Schimmel not found. Please ensure she exists in the database.')
            )
            return

        # Clear existing unpaid bills for Klara
        PaymentBreakdown.objects.filter(student=klara, is_paid=False).delete()
        
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
        
        # Overdue bills (past late_date) - should appear in overdue section
        overdue_bills = [
            {
                'student': klara,
                'description': 'May Tuition - Overdue',
                'amount': 500.00,
                'due_date': date(current_year, 5, 15),
                'date_incurred': date(current_year, 5, 1),
                'late_date': date(current_year, 5, 31),
                'is_paid': False
            },
            {
                'student': klara,
                'description': 'June Art Program - Overdue',
                'amount': 150.00,
                'due_date': date(current_year, 6, 10),
                'date_incurred': date(current_year, 6, 1),
                'late_date': date(current_year, 6, 30),
                'is_paid': False
            },
            {
                'student': klara,
                'description': 'April Music Fee - Overdue',
                'amount': 200.00,
                'due_date': date(current_year, 4, 20),
                'date_incurred': date(current_year, 4, 1),
                'late_date': date(current_year, 4, 30),
                'is_paid': False
            }
        ]
        
        # Current month bills (due by end of current month) - should appear in current month section
        current_month_bills = [
            {
                'student': klara,
                'description': f'{current_date.strftime("%B")} Tuition',
                'amount': 500.00,
                'due_date': end_of_month,
                'date_incurred': date(current_year, current_month, 1),
                'late_date': end_of_month + timedelta(days=15),
                'is_paid': False
            },
            {
                'student': klara,
                'description': f'{current_date.strftime("%B")} Art Supplies',
                'amount': 80.00,
                'due_date': end_of_month,
                'date_incurred': date(current_year, current_month, 1),
                'late_date': end_of_month + timedelta(days=15),
                'is_paid': False
            },
            {
                'student': klara,
                'description': f'{current_date.strftime("%B")} Music Program',
                'amount': 200.00,
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
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Successfully added bills for Klara Schimmel:"))
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