from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from tuition.models import Student, PaymentBreakdown


class Command(BaseCommand):
    help = 'Add future bills for all students'

    def add_arguments(self, parser):
        parser.add_argument(
            '--months',
            type=int,
            default=6,
            help='Number of months of future bills to create (default: 6)'
        )
        parser.add_argument(
            '--tuition-amount',
            type=float,
            default=500.00,
            help='Monthly tuition amount (default: 500.00)'
        )
        parser.add_argument(
            '--activity-fee',
            type=float,
            default=50.00,
            help='Monthly activity fee amount (default: 50.00)'
        )
        parser.add_argument(
            '--lunch-fee',
            type=float,
            default=100.00,
            help='Monthly lunch program fee (default: 100.00)'
        )

    def handle(self, *args, **options):
        months = options['months']
        tuition_amount = options['tuition_amount']
        activity_fee = options['activity_fee']
        lunch_fee = options['lunch_fee']
        
        # Get all active students
        students = Student.objects.filter(status='active')
        
        if not students.exists():
            self.stdout.write(
                self.style.WARNING('No active students found in the system.')
            )
            return
        
        self.stdout.write(f'Found {students.count()} active students')
        self.stdout.write(f'Creating {months} months of future bills...')
        
        # Calculate start date (next month)
        today = timezone.now().date()
        start_month = today.replace(day=1) + timedelta(days=32)
        start_month = start_month.replace(day=1)
        
        total_bills_created = 0
        
        for student in students:
            self.stdout.write(f'Processing {student.first_name} {student.last_name}...')
            student_bills_created = 0
            
            for i in range(months):
                # Calculate the month for this iteration
                current_month = start_month + timedelta(days=32 * i)
                current_month = current_month.replace(day=1)
                
                # Calculate due dates (typically 10th of each month for tuition)
                tuition_due_date = current_month.replace(day=10)
                activity_due_date = current_month.replace(day=15)
                lunch_due_date = current_month.replace(day=20)
                
                # Calculate late dates (last day of the month)
                if current_month.month == 12:
                    late_date = current_month.replace(year=current_month.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    late_date = current_month.replace(month=current_month.month + 1, day=1) - timedelta(days=1)
                
                # Check if bills already exist for this month
                existing_bills = PaymentBreakdown.objects.filter(
                    student=student,
                    due_date__year=current_month.year,
                    due_date__month=current_month.month
                )
                
                if existing_bills.exists():
                    self.stdout.write(f'  Skipping {current_month.strftime("%B %Y")} - bills already exist')
                    continue
                
                # Create tuition bill
                PaymentBreakdown.objects.create(
                    student=student,
                    description=f'{current_month.strftime("%B %Y")} Tuition',
                    amount=tuition_amount,
                    due_date=tuition_due_date,
                    date_incurred=current_month,
                    late_date=late_date,
                    is_paid=False,
                    show_in_payment_history=True
                )
                student_bills_created += 1
                
                # Create activity fee bill
                PaymentBreakdown.objects.create(
                    student=student,
                    description=f'{current_month.strftime("%B %Y")} Activity Fee',
                    amount=activity_fee,
                    due_date=activity_due_date,
                    date_incurred=current_month,
                    late_date=late_date,
                    is_paid=False,
                    show_in_payment_history=True
                )
                student_bills_created += 1
                
                # Create lunch program bill (optional - only for some students)
                if student.id in [7, 8]:  # Kurt and Klara Schimmel
                    PaymentBreakdown.objects.create(
                        student=student,
                        description=f'{current_month.strftime("%B %Y")} Lunch Program',
                        amount=lunch_fee,
                        due_date=lunch_due_date,
                        date_incurred=current_month,
                        late_date=late_date,
                        is_paid=False,
                        show_in_payment_history=True
                    )
                    student_bills_created += 1
                
                self.stdout.write(f'  Created {current_month.strftime("%B %Y")} bills')
            
            total_bills_created += student_bills_created
            self.stdout.write(
                self.style.SUCCESS(f'  Created {student_bills_created} bills for {student.first_name} {student.last_name}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {total_bills_created} future bills for {students.count()} students'
            )
        )
        
        # Show summary
        self.stdout.write('\nBill Summary:')
        self.stdout.write(f'- Tuition: ${tuition_amount:.2f} per month')
        self.stdout.write(f'- Activity Fee: ${activity_fee:.2f} per month')
        self.stdout.write(f'- Lunch Program: ${lunch_fee:.2f} per month (for select students)')
        self.stdout.write(f'- Total months: {months}')
        self.stdout.write(f'- Total bills created: {total_bills_created}') 