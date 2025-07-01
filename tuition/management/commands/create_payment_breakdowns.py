from django.core.management.base import BaseCommand
from django.utils import timezone
from tuition.models import Student, PaymentBreakdown
from datetime import datetime, timedelta
import calendar

class Command(BaseCommand):
    help = 'Creates payment breakdown items for all students'

    def handle(self, *args, **options):
        # Get all students
        students = Student.objects.all()
        
        # Get current month and year using system datetime instead of Django timezone
        # Django timezone.now() seems to be showing incorrect date
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        
        # Create payment items for each student for current month and next two months
        for student in students:
            for month_offset in range(3):  # Current month and next two months
                # Calculate month and year for this iteration
                month = current_month + month_offset
                year = current_year
                if month > 12:
                    month = month - 12
                    year += 1
                
                # Get last day of the month
                last_day = calendar.monthrange(year, month)[1]
                due_date = datetime(year, month, last_day).date()
                
                # Create tuition payment
                PaymentBreakdown.objects.create(
                    student=student,
                    description='Monthly Tuition',
                    amount=500.00,
                    due_date=due_date,
                    is_paid=False
                )
                
                # Create lunch payment
                PaymentBreakdown.objects.create(
                    student=student,
                    description='Monthly Lunch Program',
                    amount=100.00,
                    due_date=due_date,
                    is_paid=False
                )
                
                # Create activity fee
                PaymentBreakdown.objects.create(
                    student=student,
                    description='Monthly Activity Fee',
                    amount=50.00,
                    due_date=due_date,
                    is_paid=False
                )
                
                # Add a one-time field trip fee for the second month
                if month_offset == 1:
                    PaymentBreakdown.objects.create(
                        student=student,
                        description='Field Trip Fee',
                        amount=75.00,
                        due_date=due_date,
                        is_paid=False
                    )
                
                # Add a one-time technology fee for the third month
                if month_offset == 2:
                    PaymentBreakdown.objects.create(
                        student=student,
                        description='Technology Fee',
                        amount=150.00,
                        due_date=due_date,
                        is_paid=False
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created payment items for {student.first_name} {student.last_name}')
            ) 