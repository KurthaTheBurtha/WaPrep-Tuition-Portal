from django.core.management.base import BaseCommand
from django.utils import timezone
from tuition.models import PaymentBreakdown
from datetime import datetime, date
import calendar

class Command(BaseCommand):
    help = 'Check and fix any bills with incorrect dates'

    def handle(self, *args, **options):
        # Get current date using system datetime instead of Django timezone
        # Django timezone.now() seems to be showing incorrect date
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        
        self.stdout.write(f'System date: {now.strftime("%B %Y")}')
        self.stdout.write(f'Django timezone.now(): {timezone.now().strftime("%B %Y")}')
        
        # Check for bills with future dates that shouldn't exist yet
        future_bills = PaymentBreakdown.objects.filter(
            due_date__year__gt=current_year
        ).exclude(
            due_date__year=current_year,
            due_date__month=current_month
        )
        
        if future_bills.exists():
            self.stdout.write(f'Found {future_bills.count()} bills with future dates:')
            for bill in future_bills:
                self.stdout.write(f'  - {bill.student}: {bill.description} due {bill.due_date}')
            
            # Ask for confirmation to fix
            response = input('\nDo you want to fix these dates? (y/n): ')
            if response.lower() == 'y':
                for bill in future_bills:
                    # Set to current month
                    last_day = calendar.monthrange(current_year, current_month)[1]
                    bill.due_date = date(current_year, current_month, last_day)
                    bill.save()
                    self.stdout.write(f'Fixed: {bill.student} - {bill.description} now due {bill.due_date}')
                
                self.stdout.write(self.style.SUCCESS('Successfully fixed all future dates!'))
            else:
                self.stdout.write('No changes made.')
        else:
            self.stdout.write(self.style.SUCCESS('No bills with incorrect future dates found.'))
        
        # Show current month's bills
        current_month_bills = PaymentBreakdown.objects.filter(
            due_date__year=current_year,
            due_date__month=current_month
        )
        
        if current_month_bills.exists():
            self.stdout.write(f'\nCurrent month ({now.strftime("%B %Y")}) bills:')
            for bill in current_month_bills:
                self.stdout.write(f'  - {bill.student}: {bill.description} due {bill.due_date}')
        else:
            self.stdout.write(f'\nNo bills found for current month ({now.strftime("%B %Y")})') 