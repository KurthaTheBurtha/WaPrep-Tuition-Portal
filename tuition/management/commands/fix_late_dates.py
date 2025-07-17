from django.core.management.base import BaseCommand
from tuition.models import PaymentBreakdown
from datetime import datetime
import calendar


class Command(BaseCommand):
    help = 'Fix late_date fields for existing PaymentBreakdown records'

    def handle(self, *args, **options):
        # Get all PaymentBreakdown records that don't have late_date set
        bills_without_late_date = PaymentBreakdown.objects.filter(late_date__isnull=True)
        
        self.stdout.write(f"Found {bills_without_late_date.count()} bills without late_date")
        
        updated_count = 0
        for bill in bills_without_late_date:
            # Use due_date if available, otherwise date_incurred, otherwise today
            ref_date = bill.due_date or bill.date_incurred or datetime.now().date()
            
            # Calculate last day of the month
            last_day_of_month = calendar.monthrange(ref_date.year, ref_date.month)[1]
            bill.late_date = datetime(ref_date.year, ref_date.month, last_day_of_month).date()
            
            bill.save(update_fields=['late_date'])
            updated_count += 1
            
            self.stdout.write(f"Updated bill {bill.id} ({bill.description}) - late_date: {bill.late_date}")
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully updated {updated_count} bills with late_date")
        ) 