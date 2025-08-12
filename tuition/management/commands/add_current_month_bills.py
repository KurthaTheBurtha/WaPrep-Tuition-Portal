from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from tuition.models import Student, PaymentBreakdown


class Command(BaseCommand):
    help = 'Add bills for the current month for Kurt and Klara Schimmel'

    def add_arguments(self, parser):
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
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating bills'
        )

    def handle(self, *args, **options):
        tuition_amount = Decimal(str(options['tuition_amount']))
        activity_fee = Decimal(str(options['activity_fee']))
        lunch_fee = Decimal(str(options['lunch_fee']))
        dry_run = options['dry_run']
        
        # Get current month
        today = timezone.now().date()
        current_month = today.replace(day=1)
        
        self.stdout.write(f'Current month: {current_month.strftime("%B %Y")}')
        
        # Find Kurt and Klara Schimmel
        try:
            kurt = Student.objects.get(first_name='Kurt', last_name='Schimmel')
            klara = Student.objects.get(first_name='Klara', last_name='Schimmel')
        except Student.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Kurt or Klara Schimmel not found. Please ensure they exist in the database.')
            )
            return
        
        students = [kurt, klara]
        bills_to_create = []
        
        for student in students:
            self.stdout.write(f'Processing {student.first_name} {student.last_name}...')
            
            # Check if bills already exist for this month
            existing_bills = PaymentBreakdown.objects.filter(
                student=student,
                date_incurred__year=current_month.year,
                date_incurred__month=current_month.month
            )
            
            if existing_bills.exists():
                self.stdout.write(
                    self.style.WARNING(f'  Bills already exist for {student.first_name} this month:')
                )
                for bill in existing_bills:
                    self.stdout.write(f'    - {bill.description}: ${bill.amount} (Paid: {bill.is_paid})')
                continue
            
            # Calculate due dates (typically 10th of each month for tuition)
            tuition_due_date = current_month.replace(day=10)
            activity_due_date = current_month.replace(day=15)
            lunch_due_date = current_month.replace(day=20)
            
            # Calculate late date (last day of the month)
            if current_month.month == 12:
                late_date = current_month.replace(year=current_month.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                late_date = current_month.replace(month=current_month.month + 1, day=1) - timedelta(days=1)
            
            # Create tuition bill
            tuition_bill = {
                'student': student,
                'description': f'{current_month.strftime("%B %Y")} Tuition',
                'amount': tuition_amount,
                'currency': 'USD',
                'due_date': tuition_due_date,
                'date_incurred': current_month,
                'late_date': late_date,
                'is_paid': False,
                'show_in_payment_history': True
            }
            bills_to_create.append(tuition_bill)
            
            # Create activity fee bill
            activity_bill = {
                'student': student,
                'description': f'{current_month.strftime("%B %Y")} Activity Fee',
                'amount': activity_fee,
                'currency': 'USD',
                'due_date': activity_due_date,
                'date_incurred': current_month,
                'late_date': late_date,
                'is_paid': False,
                'show_in_payment_history': True
            }
            bills_to_create.append(activity_bill)
            
            # Create lunch program bill (for Kurt and Klara)
            lunch_bill = {
                'student': student,
                'description': f'{current_month.strftime("%B %Y")} Lunch Program',
                'amount': lunch_fee,
                'currency': 'USD',
                'due_date': lunch_due_date,
                'date_incurred': current_month,
                'late_date': late_date,
                'is_paid': False,
                'show_in_payment_history': True
            }
            bills_to_create.append(lunch_bill)
            
            self.stdout.write(f'  Would create 3 bills for {student.first_name}:')
            self.stdout.write(f'    - Tuition: ${tuition_amount} (Due: {tuition_due_date})')
            self.stdout.write(f'    - Activity Fee: ${activity_fee} (Due: {activity_due_date})')
            self.stdout.write(f'    - Lunch Program: ${lunch_fee} (Due: {lunch_due_date})')
        
        if not bills_to_create:
            self.stdout.write(
                self.style.WARNING('No bills to create - all students already have bills for this month.')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\nDRY RUN: Would create {len(bills_to_create)} bills for Kurt and Klara')
            )
            return
        
        # Create the bills
        created_bills = []
        for bill_data in bills_to_create:
            try:
                bill = PaymentBreakdown.objects.create(**bill_data)
                created_bills.append(bill)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating bill for {bill_data["student"].first_name}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully created {len(created_bills)} bills for Kurt and Klara')
        )
        
        # Show summary
        self.stdout.write('\nBill Summary:')
        self.stdout.write(f'- Tuition: ${tuition_amount:.2f} per student')
        self.stdout.write(f'- Activity Fee: ${activity_fee:.2f} per student')
        self.stdout.write(f'- Lunch Program: ${lunch_fee:.2f} per student')
        self.stdout.write(f'- Total bills created: {len(created_bills)}')
        self.stdout.write(f'- Total amount per student: ${(tuition_amount + activity_fee + lunch_fee):.2f}')
        self.stdout.write(f'- Total amount for both students: ${(tuition_amount + activity_fee + lunch_fee) * 2:.2f}')
        
        self.stdout.write('\nTo view the bills:')
        self.stdout.write('- Go to Admin Dashboard > Manage Billing')
        self.stdout.write('- Click on Kurt or Klara to see their bills')
        self.stdout.write('- Or go to Students > Select student > Bills') 